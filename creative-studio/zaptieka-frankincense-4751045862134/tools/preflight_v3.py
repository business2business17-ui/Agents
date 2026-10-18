from pathlib import Path
import subprocess,sys,json,os
from PIL import Image,ImageCms
project=Path(__file__).resolve().parents[1]
root=Path(__file__).resolve().parents[3]
assets=json.loads((project/'v3/manifest.json').read_text(encoding='utf8'))
checks=[]
for a in assets:
    f=project/'v3'/a['file']
    result=subprocess.run([sys.executable,str(root/'plugins/amazon-creative-studio/skills/amazon-creative-studio/scripts/validate_asset.py'),str(f),'--placement',a['placement'],'--expect',a['dimensions'].replace(' ',''),'--json'],capture_output=True,text=True,encoding='utf8',env={**os.environ,'PYTHONIOENCODING':'utf-8'})
    im=Image.open(f)
    checks.append({'asset':a['file'],'validator_exit':result.returncode,'result':result.stdout,'stderr':result.stderr,'icc':ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(__import__('io').BytesIO(im.info['icc_profile']))),'size':im.size,'bytes':f.stat().st_size})
(project/'v3/PREFLIGHT.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps([{'asset':c['asset'],'exit':c['validator_exit'],'size':c['size'],'bytes':c['bytes']} for c in checks],ensure_ascii=False))
