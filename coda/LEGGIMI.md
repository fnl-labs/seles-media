# Coda di pubblicazione

Un file `.json` qui dentro = un post che uscirà da solo alla sua ora.
Il workflow controlla ogni 10 minuti; quando l'orario è passato pubblica e
sposta il file in `../pubblicati/` con dentro i link dei post usciti.

```json
{
  "quando": "2026-09-27T00:00:00+02:00",
  "dove": ["ig", "fb"],
  "immagini": ["media/20260927-match-c11.jpg"],
  "didascalia": "testo del post"
}
```

- `quando`: ora italiana, con il fuso (`+02:00` d'estate, `+01:00` d'inverno).
- `dove`: `ig`, `fb`, o entrambi.
- `immagini`: percorsi dentro questa repo (fino a 10 = carosello).
- GitHub può far partire il controllo con qualche minuto di ritardo: normale.
