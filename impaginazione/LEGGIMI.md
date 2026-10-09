# Impaginazione ricostruita di Gold Man (round 1)

`correzioni_round1/GOLD MAN_print_rev1.pdf` è l'interno ricomposto con tutte le correzioni del markup di Chloe applicate. Il testo è preso parola per parola dal PDF consegnato.

Il layout riprende quello originale:
- formato 5×8", griglia 11/16 pt, 28 righe;
- margini a specchio e rientro di 14,2 pt;
- Adobe Garamond Pro (i sottoinsiemi incorporati nel PDF originale);
- aperture dei capitoli con il sole, AvantGarde per titoli e sottotitoli;
- ornamento per i cambi scena, folio Montserrat con filetto oro;
- colori oro in CMYK identici all'originale.

## Script

| File | Cosa fa |
|---|---|
| `model.py` | Legge il PDF di markup, ricostruisce paragrafi, rientri, corsivi, capitoli e cambi scena, e applica le annotazioni (sostituzioni, eliminazioni, inserimenti, corsivo, unioni di paragrafi). Sulle doppie correzioni vince la più recente. Produce `doc.json`. |
| `gen.py` | Genera l'HTML con frontespizio, copyright, dedica, nota dell'autrice, mappa e corpo. Il terzo argomento è il nome del credito tipografico. |
| `mkfont2.py` | Converte i font CFF estratti dal PDF in OTF (legature fi/fl/ff/Th) e aggiunge i pochi glifi mancanti da EB Garamond/DejaVu. |
| `sun.svg`, `orn.svg`, `rule_*.svg` | Grafica vettoriale estratta dal PDF originale, in CMYK. |

Il PDF si ottiene con WeasyPrint: `python3 -c "import weasyprint; weasyprint.HTML('book.html').write_pdf('book.pdf')"`.

I font non sono nel repository, perché sono font Adobe con licenza. Si rigenerano estraendoli dal PDF originale.
