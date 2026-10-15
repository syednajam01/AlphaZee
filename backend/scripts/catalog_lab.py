"""Export selected catalog data; dry-run/apply it only in the checkout lab."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text
from app.database import engine,SessionLocal
from app.services.catalog_transfer import export_bundle,import_bundle

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='action',required=True)
    export=commands.add_parser('export')
    export.add_argument('--product',action='append',required=True,help='Stable product ID; repeat to select multiple products')
    export.add_argument('--output',required=True)
    export.add_argument('--include-supplier-costs',action='store_true',help='Copy active mapping cost only; excludes supplier identity/contact details')
    imp=commands.add_parser('import')
    imp.add_argument('bundle');imp.add_argument('--owner',required=True)
    imp.add_argument('--stock',type=int,default=0,help='Explicit starting quantity per mapped variant; never copies source stock/holds')
    imp.add_argument('--apply',action='store_true',help='Default is validation/dry run')
    args=parser.parse_args()
    if args.action=='export':
        with engine.connect().execution_options(isolation_level='REPEATABLE READ') as connection:
            with connection.begin():
                connection.execute(text('SET TRANSACTION READ ONLY'))
                from sqlalchemy.orm import Session
                with Session(bind=connection) as db:
                    bundle=export_bundle(db,args.product,args.output,args.include_supplier_costs)
                    print(json.dumps({'products':[p.source_id for p in bundle.products], 'media_count':len(bundle.assets),'source_read_only':True,'output':args.output}))
    else:
        with SessionLocal() as db: print(json.dumps(import_bundle(db,args.bundle,args.owner,args.stock,args.apply)))

if __name__=='__main__':main()
