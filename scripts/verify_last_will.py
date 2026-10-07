# SPDX-License-Identifier: MIT
"""P42 independent MQTT byte fixtures plus XMQR's rumqttc CLI; no Mosquitto."""
import argparse, importlib.util, socket, struct, subprocess, tempfile, unittest, sys
from pathlib import Path

sys.dont_write_bytecode = True
SPEC=importlib.util.spec_from_file_location('fixtures',Path(__file__).parent/'verify_interop.py')
fixtures=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(fixtures)

class WillClient(fixtures.WireClient):
    def __init__(self,broker,cid,topic,payload,qos=0,retain=False,clean=True,keepalive=30,flags=None):
        self.socket=socket.create_connection(('127.0.0.1',broker.port),timeout=fixtures.TIMEOUT)
        flag=(2 if clean else 0)|4|(qos<<3)|(32 if retain else 0)
        if flags is not None: flag=flags
        body=fixtures.text('MQTT')+bytes([4,flag])+struct.pack('!H',keepalive)+fixtures.text(cid)
        body+=fixtures.text(topic)+struct.pack('!H',len(payload))+payload
        self.send(0x10,body);self.connack=self.receive()
        assert self.connack==(0x20,b'\0\0')

def publication(client):
    header,body=client.receive();assert header>>4==3,(header,body)
    length=int.from_bytes(body[:2]);topic=body[2:2+length].decode();offset=2+length
    qos=(header>>1)&3;retained=bool(header&1)
    if qos:
        identifier=body[offset:offset+2];offset+=2
        client.send(0x40 if qos==1 else 0x50,identifier)
        if qos==2:
            assert client.receive()==(0x62,identifier)
            client.send(0x70,identifier)
    return topic,qos,retained,body[offset:]

def no_message(client):
    client.socket.settimeout(.25)
    try:
        client.receive()
    except socket.timeout: return
    finally: client.socket.settimeout(fixtures.TIMEOUT)
    raise AssertionError('unexpected duplicate/publication')

class LastWillIntegration(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='xmqr-p42-')
        self.broker=fixtures.Broker(self.directory.name)
        self.addCleanup(self.directory.cleanup);self.addCleanup(self.broker.stop)
        self.broker.start()
    def observer(self,cid='observer',topic='status/device',clean=True):
        client=fixtures.WireClient(self.broker,cid,clean)
        self.addCleanup(client.close)
        assert client.subscribe([(topic,2)])==(0x90,b'\0\x01\x02')
        return client
    def test_will_qos_0_1_2_and_both_clean_session_modes(self):
        for clean in (True,False):
            for qos in (0,1,2):
                with self.subTest(clean=clean,qos=qos):
                    observer=self.observer(f'obs{int(clean)}{qos}')
                    client=WillClient(self.broker,f'pub{int(clean)}{qos}','status/device',b'offline',qos,clean=clean)
                    client.close()
                    self.assertEqual(publication(observer),('status/device',qos,False,b'offline'))
                    no_message(observer);observer.send(0xe0);observer.close()
    def test_disconnect_cancels_will_durably(self):
        client=WillClient(self.broker,'normal','status/device',b'cancelled',2,True,clean=False)
        client.send(0xe0)
        self.assertEqual(client.socket.recv(1),b'');client.close()
        self.broker.stop();self.broker.start()
        observer=self.observer();no_message(observer)
    def test_keepalive_timeout_publishes_will(self):
        observer=self.observer()
        client=WillClient(self.broker,'timeout','status/device',b'timeout',1,keepalive=1)
        self.addCleanup(client.close)
        self.assertEqual(publication(observer),('status/device',1,False,b'timeout'))
        self.assertEqual(client.socket.recv(1),b'');no_message(observer)
    def test_takeover_publishes_old_will_once(self):
        observer=self.observer()
        old=WillClient(self.broker,'same','status/device',b'old',1,clean=False)
        self.addCleanup(old.close)
        new=fixtures.WireClient(self.broker,'same',False);self.addCleanup(new.close)
        self.assertEqual(publication(observer),('status/device',1,False,b'old'))
        self.assertEqual(old.socket.recv(1),b'');no_message(observer)
    def test_protocol_error_publishes_accepted_will(self):
        observer=self.observer()
        client=WillClient(self.broker,'malformed','status/device',b'protocol-error',1)
        self.addCleanup(client.close)
        client.send(0xff)
        self.assertEqual(publication(observer),('status/device',1,False,b'protocol-error'))
        self.assertEqual(client.socket.recv(1),b'');no_message(observer)
    def test_crash_recovery_utf8_1024_offline_retained_and_no_repeat(self):
        topic='é'*512
        observer=self.observer('persistent',topic,False)
        source=WillClient(self.broker,'source',topic,b'crash',2,True,clean=True)
        self.addCleanup(source.close)
        self.broker.stop();observer.close();source.close();self.broker.start()
        resumed=fixtures.WireClient(self.broker,'persistent',False);self.addCleanup(resumed.close)
        self.assertEqual(resumed.connack,(0x20,b'\x01\0'))
        self.assertEqual(publication(resumed),(topic,2,False,b'crash'));resumed.ping();no_message(resumed)
        late=self.observer('late',topic)
        self.assertEqual(publication(late),(topic,2,True,b'crash'));late.ping()
        self.broker.stop();resumed.close();late.close();self.broker.start()
        again=fixtures.WireClient(self.broker,'persistent',False);self.addCleanup(again.close)
        no_message(again)
    def test_cli_retained_replace_delete_and_wildcard(self):
        def publish(payload):
            args=[str(CLIENT),'pub','--open-lab','--host','127.0.0.1','--port',str(self.broker.port),'--topic','sensor/value','--message',payload,'--qos','2','--retain','true']
            subprocess.run(args,check=True,capture_output=True,timeout=fixtures.TIMEOUT)
        publish('one');publish('two')
        observer=self.observer('wildcard','sensor/+',False)
        self.assertEqual(publication(observer),('sensor/value',2,True,b'two'))
        observer.ping()
        publish('')
        self.assertEqual(publication(observer),('sensor/value',2,False,b''));observer.ping()
        self.broker.stop();observer.close();self.broker.start()
        late=self.observer('late','sensor/#');no_message(late)
    def test_invalid_will_flags_close_without_accepting(self):
        for flags in (0x1e,0x0a,0x22,0x07):
            client=fixtures.WireClient.__new__(fixtures.WireClient)
            client.socket=socket.create_connection(('127.0.0.1',self.broker.port),timeout=fixtures.TIMEOUT)
            with client:
                client.send(0x10,fixtures.text('MQTT')+bytes([4,flags,0,30])+fixtures.text('bad')+fixtures.text('status/device')+b'\0\x03bad')
                self.assertEqual(client.socket.recv(1),b'')
    def test_cli_last_will_on_process_crash(self):
        observer=self.observer()
        args=[str(CLIENT),'sub','--open-lab','--host','127.0.0.1','--port',str(self.broker.port),'--topic','unused/topic','--will-topic','status/device','--will-message','cli-crash','--will-qos','2','--will-retain','true']
        process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        try:
            assert 'Assinatura ativa' in process.stdout.readline()
            process.kill();process.wait(timeout=fixtures.TIMEOUT)
            self.assertEqual(publication(observer),('status/device',2,False,b'cli-crash'))
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=fixtures.TIMEOUT)
            process.stdout.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--broker',type=Path,required=True);parser.add_argument('--client',type=Path,required=True)
    args=parser.parse_args();fixtures.BROKER=args.broker.resolve();CLIENT=args.client.resolve()
    unittest.main(argv=['verify-last-will'],verbosity=2)
