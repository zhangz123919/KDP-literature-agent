
from io import BytesIO
import pandas as pd
from docx import Document
def excel_bytes(df,sheet="结果"):
    b=BytesIO()
    with pd.ExcelWriter(b,engine="openpyxl") as w:df.to_excel(w,sheet_name=sheet[:31],index=False)
    return b.getvalue()
def docx_bytes(title,text,sources=None):
    d=Document();d.add_heading(title,0)
    for line in str(text or "").splitlines():
        s=line.strip()
        if not s:continue
        if s.startswith("### "):d.add_heading(s[4:],3)
        elif s.startswith("## "):d.add_heading(s[3:],2)
        elif s.startswith("# "):d.add_heading(s[2:],1)
        elif s.startswith("- "):d.add_paragraph(s[2:],style="List Bullet")
        else:d.add_paragraph(s.replace("**",""))
    if sources:
        d.add_heading("依据文献",1)
        for x in sources:d.add_paragraph(f"[{x['编号']}] {x['题名']} ({x['年份']}) DOI:{x['DOI']}",style="List Bullet")
    b=BytesIO();d.save(b);return b.getvalue()
