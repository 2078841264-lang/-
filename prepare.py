from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image,ImageOps,ImageDraw
out=Path('tmp/translation');out.mkdir(parents=True,exist_ok=True)
d=pdfium.PdfDocument(r'C:\Users\luluxiu\Downloads\MorphQuad-Morphable Quadrotor for Superhuman.pdf')
for i in range(len(d)):
    im=d[i].render(scale=2).to_pil(); im.save(out/f'source-{i+1}.png')
for nums,name in [([32,33,34,35,36,37,38],'math-main'),([49,50,51,52,53,54,55],'math-supp'),([3,5,8,10,12,18,22,24,31],'figures')]:
    sheet=Image.new('RGB',(350*4,510*((len(nums)+3)//4)),'#dddddd')
    for j,n in enumerate(nums):
        im=Image.open(out/f'source-{n}.png');im.thumbnail((340,480));sheet.paste(im,(350*(j%4),510*(j//4)+25));ImageDraw.Draw(sheet).text((350*(j%4)+10,510*(j//4)+5),str(n),fill='black')
    sheet.save(out/f'{name}.jpg')
