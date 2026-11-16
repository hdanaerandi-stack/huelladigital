(function(){
  'use strict';
  function ascii(v){
    return String(v??'')
      .normalize('NFD').replace(/[\u0300-\u036f]/g,'')
      .replace(/[“”]/g,'"').replace(/[‘’]/g,"'")
      .replace(/[^\x20-\x7E\n\r]/g,'?');
  }
  function escPdf(v){return ascii(v).replace(/\\/g,'\\\\').replace(/\(/g,'\\(').replace(/\)/g,'\\)');}
  function wrap(text,max=88){
    const paras=ascii(text).split(/\r?\n/); const lines=[];
    for(const para of paras){
      const words=para.split(/\s+/).filter(Boolean); let line='';
      if(!words.length){lines.push('');continue;}
      for(const w of words){
        const test=line?line+' '+w:w;
        if(test.length>max && line){lines.push(line);line=w;}else line=test;
      }
      if(line)lines.push(line);
    }
    return lines;
  }
  function buildRecipeLines(r){
    const date = r.date ? new Date(r.date).toLocaleDateString('es-MX') : new Date().toLocaleDateString('es-MX');
    const lines=[
      {t:'HUELLA - RECETA VETERINARIA',size:18,bold:true},
      {t:'Fecha: '+date,size:10},
      {t:'',size:8},
      {t:'Mascota: '+(r.pet||'Sin nombre'),size:13,bold:true},
      {t:'Tutor: '+(r.owner||'No registrado'),size:10},
      {t:'',size:8},
      {t:'DIAGNOSTICO',size:11,bold:true},
      ...wrap(r.diagnosis||'Sin diagnostico').map(t=>({t,size:10})),
      {t:'',size:8},
      {t:'MEDICAMENTO / TRATAMIENTO',size:11,bold:true},
      ...wrap(r.medication||'Sin tratamiento').map(t=>({t,size:10})),
      {t:'',size:8},
      {t:'INDICACIONES',size:11,bold:true},
      ...wrap(r.instructions||'Sin indicaciones').map(t=>({t,size:10})),
      {t:'',size:10},
      {t:'Veterinario: '+(r.vet||'No registrado'),size:10,bold:true},
      {t:'Cedula profesional: '+(r.license||'No registrada'),size:10},
      {t:'',size:9},
      {t:'Documento generado por Huella. Verifique indicaciones y datos profesionales.',size:8}
    ];
    return lines.slice(0,42);
  }
  function makePdf(lines){
    let y=760; const parts=[];
    for(const line of lines){
      const size=line.size||10;
      const font=line.bold?'F2':'F1';
      parts.push(`BT /${font} ${size} Tf 55 ${y} Td (${escPdf(line.t)}) Tj ET`);
      y -= line.t ? Math.max(15,size+5) : 10;
    }
    const stream=parts.join('\n');
    const objs=[];
    objs.push('1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj');
    objs.push('2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj');
    objs.push('3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >> endobj');
    objs.push(`4 0 obj << /Length ${stream.length} >> stream\n${stream}\nendstream endobj`);
    objs.push('5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj');
    objs.push('6 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj');
    let pdf='%PDF-1.4\n'; const offsets=[0];
    for(const o of objs){offsets.push(pdf.length);pdf+=o+'\n';}
    const xref=pdf.length;
    pdf+=`xref\n0 ${objs.length+1}\n0000000000 65535 f \n`;
    for(let i=1;i<=objs.length;i++) pdf+=String(offsets[i]).padStart(10,'0')+' 00000 n \n';
    pdf+=`trailer << /Size ${objs.length+1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
    return new Blob([pdf],{type:'application/pdf'});
  }
  function downloadRecipe(r,filename){
    const blob=makePdf(buildRecipeLines(r));
    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download=filename||`Receta_${ascii(r.pet||'mascota').replace(/\s+/g,'_')}.pdf`;
    document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1500);
  }
  window.HuellaPDF={downloadRecipe};
})();
