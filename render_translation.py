from pathlib import Path
import importlib.util,os,tempfile,json
from PIL import Image,ImageDraw
from pypdf import PdfReader
root=Path.cwd();tmp=root/'tmp/translation';rend=tmp/'rendered';rend.mkdir(exist_ok=True)
skill=Path(r'C:\Users\luluxiu\.codex\plugins\cache\openai-primary-runtime\documents\26.905.11957\skills\documents\render_docx.py')
spec=importlib.util.spec_from_file_location('docx_renderer',skill);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
# The bundled Windows runtime has no LibreOffice. Use the actual Word export
# as the input to the skill's unchanged Poppler rasterization stage.
mod.convert_to_pdf=lambda *args,**kwargs:(str(tmp/'word-preview.pdf'),'Microsoft Word PDF export')
os.environ['PATH']=r'C:\Users\luluxiu\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin'+os.pathsep+os.environ['PATH']
tempfile.tempdir=str(tmp)
paths=mod.rasterize(str(root/'output/MorphQuad_完整中文译文.docx'),str(rend),140,False,False)
print('PAGES',len(paths))
pdf=PdfReader(tmp/'word-preview.pdf')
for i,p in enumerate(pdf.pages):
    print(i+1,len(p.extract_text()),p.extract_text()[:65].replace('\n',' '))
for start in range(0,len(paths),8):
    sheet=Image.new('RGB',(4*420,2*620),'#dddddd');dr=ImageDraw.Draw(sheet)
    for j,path in enumerate(paths[start:start+8]):
        im=Image.open(path);im.thumbnail((410,585));x=420*(j%4);y=620*(j//4)
        sheet.paste(im,(x,y+25));dr.text((x+10,y+5),str(start+j+1),fill='black')
    sheet.save(tmp/f'qa-{start+1}.jpg')
