"""Generate original, reusable PNG icons. Requires Pillow only for regeneration."""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
S = 3
palette = {"agent":"#5856D6", "approval":"#3B55C6", "question":"#0094A8", "complete":"#198754", "warning":"#D45B29", "code":"#4049A8", "project":"#B07C13", "server":"#28768E"}

def icon(name):
    im = Image.new("RGBA", (256*S, 256*S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    def box(x): return tuple(int(i*S) for i in x)
    def line(xy, width=12): d.line([tuple(int(v*S) for v in pt) for pt in xy], fill="white", width=width*S, joint="curve")
    d.rounded_rectangle(box((5,5,251,251)),radius=63*S,fill=palette[name])
    if name == "agent":
        d.rounded_rectangle(box((48,71,208,188)),radius=30*S,outline="white",width=12*S)
        d.ellipse(box((79,111,96,128)),fill="white"); d.ellipse(box((160,111,177,128)),fill="white")
        line([(96,155),(160,155)],10); line([(128,43),(128,69)],10); d.ellipse(box((119,31,137,49)),fill="white")
    elif name == "approval":
        d.rounded_rectangle(box((60,103,196,202)),radius=18*S,outline="white",width=12*S)
        d.arc(box((83,49,173,153)),180,360,fill="white",width=12*S)
        line([(102,150),(120,168),(157,128)],11)
    elif name == "question":
        d.rounded_rectangle(box((44,55,212,172)),radius=28*S,outline="white",width=12*S)
        line([(79,172),(70,203),(111,175)],10)
        d.arc(box((99,72,157,129)),200,540,fill="white",width=12*S); line([(128,125),(128,137)],10)
        d.ellipse(box((123,147,133,157)),fill="white")
    elif name == "complete":
        d.ellipse(box((45,45,211,211)),outline="white",width=12*S); line([(78,130),(113,165),(181,94)],14)
    elif name == "warning":
        d.line([box((128,45)),box((216,199)),box((40,199)),box((128,45))],fill="white",width=12*S,joint="curve")
        line([(128,99),(128,148)],12); d.ellipse(box((121,164,135,178)),fill="white")
    elif name == "code":
        line([(91,79),(52,128),(91,177)],13); line([(165,79),(204,128),(165,177)],13); line([(147,60),(109,196)],11)
    elif name == "project":
        d.rounded_rectangle(box((39,76,217,193)),radius=17*S,outline="white",width=12*S)
        line([(42,90),(42,60),(100,60),(117,76)],12)
        line([(74,120),(179,120)],10); line([(74,151),(145,151)],10)
    elif name == "server":
        for y in (55,108,161):
            d.rounded_rectangle(box((48,y,208,y+40)),radius=9*S,outline="white",width=9*S)
            d.ellipse(box((65,y+14,77,y+26)),fill="white"); line([(102,y+20),(179,y+20)],7)
    im.resize((256,256),Image.Resampling.LANCZOS).save(OUT/f"{name}.png", optimize=True)

for name in palette: icon(name)
