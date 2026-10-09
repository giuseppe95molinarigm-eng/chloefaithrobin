# Gold Man: correzioni del round 1 (markup di Chloe, 8 ott)

Il file `Gold Man Oct 3 - CR Markup.pdf` contiene **978 annotazioni**, cioè i "977 comments" di Chloe più una nota di risposta. Corrisponde parola per parola a `GOLD MAN (1).pdf`, tranne il credito del typesetter.

| Azione | N. |
|---|---|
| Sostituisci | 564 |
| Elimina | 200 |
| Inserisci | 130 |
| Nuovo paragrafo (a capo, `¶`) | 7 |
| Togli il corsivo | 34 |
| Metti in corsivo | 25 |
| Note di impaginazione (a mano) | 18 |

## File

- **`GoldMan_correzioni_round1.xlsx`**: la checklist completa, nell'ordine delle pagine. Per ogni correzione trovi la pagina del PDF di Chloe, la pagina del libro, il testo prima e dopo (per trovarla con Cerca), il testo da modificare, il nuovo testo e la nota tradotta. Nella colonna "Fatto" metti ✓ e la riga diventa verde.
  - Foglio **Da fare a mano**: front matter, logo, mappa, testo "compresso", paragrafi da unire, rientri.
  - Filtra la colonna **Script = "A mano"** per vedere anche le doppie correzioni da decidere.
- **`GoldMan_correzioni_round1.jsx`**: lo script InDesign che applica in automatico le correzioni di testo e di corsivo.

## Come usare lo script

1. **Fai una copia** di `GOLD MAN.indd`.
2. Apri la copia in InDesign.
3. Vai su Finestra › Utilità › Script, fai tasto destro su **Utente** e scegli **Mostra nel Finder**. Copia lì il file `.jsx`.
4. Fai doppio clic sullo script nel pannello Script.
5. Lo script:
   - applica solo le correzioni che trova in **un solo punto** del testo, usando il contesto prima e dopo;
   - verifica che il testo da sostituire sia esattamente quello atteso, altrimenti salta la correzione;
   - attiva le **Revisioni** (Track Changes): vedi tutte le modifiche in Editor brani (Cmd+Y) e puoi accettarle in blocco o una per una;
   - si annulla tutto con **un solo Cmd+Z**;
   - salva `GoldMan_correzioni_log.txt` accanto al file `.indd`, con l'esito di ogni correzione (il "#" è lo stesso dell'Excel) e la pagina InDesign.
6. Fai a mano quello che il log non segna come `APPLICATA`.

Nella simulazione sul testo del libro lo script ha applicato **942 correzioni su 955**. Le altre sono doppie correzioni di Chloe sullo stesso punto, da decidere a mano: per esempio #218 "he had → he'd" insieme a #219 "elimina had". È uno script mai provato dentro InDesign: per questo lavora con Revisioni attive e si annulla con un solo Cmd+Z.

> Nota: le modifiche di corsivo non compaiono nelle Revisioni, ma sono elencate nel log.

## Da fare a mano (riassunto)

- **Mappa** (`map.png`): va subito prima del PROLOGUE, su una pagina sua. È 1650×2550 px (5,5×8,5" a 300 dpi): va adattata al formato 5×8 e convertita per la stampa.
- **Frontespizio**: titolo più grande e al centro, con gli stessi font della copertina. Autrice nel terzo inferiore. Aggiungere il logo RE:BOOKS (`3.png`, RGB, da convertire in CMYK).
- **Copyright**: testo centrato e spostato nel terzo inferiore. Al posto di "Élite Publishing" vogliono il **nome del typesetter** (in `GOLD MAN (1).pdf` c'era "Elena Pensiero").
- Dedica: "Bob - Your" diventa "Bob—your", e va aggiunta una virgola.
- Note dell'autrice: sistemare la spaziatura dell'ultimo paragrafo.
- Testo "compresso" o con font strano alle pp. PDF 24, 40, 75, 235, 284: controllare tracking e scala.
- p. 74: troppo spazio in fondo pagina. p. 343: manca lo spazio tra il capitolo e il primo paragrafo.
- p. 110: unire il paragrafo al dialogo successivo. p. 160: unire al precedente.
- p. 130 e p. 327: togliere il rientro.
- Dopo il reflow: capitoli su pagina destra, pagine bianche senza numero, righe vedove/orfane.
