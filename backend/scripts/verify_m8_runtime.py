"""Read-only persistence checks around a lab API/web restart."""
import json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from verify_m1_browser import wait_http

ROOT=Path(__file__).resolve().parents[2]
LAB=['docker','compose','-f','compose.checkout-lab.yml']

def run(arguments):return subprocess.check_output(arguments,cwd=ROOT,stderr=subprocess.PIPE)

def main():
    report=json.loads((ROOT/'.context/m8_browser_verification.json').read_text())
    token=Path(report['artifacts']).name
    cmd=LAB+['exec','-T','api','python','scripts/lab_runtime.py','--snapshot-token',token]
    before=json.loads(run(cmd))
    run(LAB+['restart','api','web'])
    run(LAB+['up','--no-build','--wait','-d'])
    for url in ('http://127.0.0.1:18001/api/v1/ready','http://127.0.0.1:13001/api/v1/storefront/capabilities'):
        wait_http(url)
    after=json.loads(run(cmd));assert before==after
    normal=json.loads(wait_http('http://localhost:13000/api/v1/storefront/capabilities'))
    lab=json.loads(wait_http('http://127.0.0.1:13001/api/v1/storefront/capabilities'))
    assert not normal['checkout_enabled'] and lab['checkout_enabled'] and lab['test_mode']
    config=json.loads(run(LAB+['config','--format','json']))
    normal_config=json.loads(run(['docker','compose','--env-file','.env.docker.local','config','--format','json']))
    lab_volumes={v['name'] for v in config['volumes'].values()}
    normal_volumes={v['name'] for v in normal_config['volumes'].values()}
    assert not lab_volumes.intersection(normal_volumes)
    assert config['services']['api']['network_mode']=='service:db'
    result={'phase':'M8','checked_at_utc':datetime.now(timezone.utc).isoformat(),'snapshot':after,
        'restart_preserves_catalog_orders_media_and_stock':True,'independent_named_volumes':True,
        'lab_checkout_enabled':True,'normal_checkout_enabled':False,'normal_development_modified':False}
    (ROOT/'.context/m8_runtime_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
