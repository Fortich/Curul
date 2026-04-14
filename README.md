# Curul 🪑

**What did your congresspeople say? Find out.**

Curul takes plenary sessions from the Colombian Congress, transcribes them, and shows you exactly what each congressperson said — no noise, straight to the ideas.

## Why?

Congressional plenary sessions are public, but in practice nobody has 8 hours to watch a full debate. Curul solves that:

- **Search by congressperson.** Find what Iván Cepeda, María Fernanda Cabal, or anyone else said in seconds.
- **Hold them accountable.** Is your senator representing your interests? Now you can verify it with their own words.
- **Form your own opinion.** See different congresspeople's positions on the same topic and decide for yourself.
- **Stay up to date.** Sessions are processed shortly after they occur.

## How it works

1. Audio is downloaded from the Canal Congreso YouTube channel
2. Transcribed using Whisper
3. Speeches are extracted and attributed to each congressperson using LLMs
4. Everything is presented in a simple, searchable interface

> ⚠️ Quote attribution is automated and may contain errors. Curul is a reference tool, not an official source.

## Project status

🚧 Actively in development — MVP under construction.

## Stack

- **Pipeline:** Python, yt-dlp, Whisper, Claude API
- **Database:** SQLite
- **Frontend:** React (SPA)
- **Monorepo** with pipeline and frontend in a single repository

## Project structure

```
curul/
├── pipeline/       # Download, transcription, and idea extraction
├── frontend/       # Web application
├── db/             # Schema and migrations
└── README.md
```

## Contributing

Curul is an open project. If you care about legislative transparency in Colombia, you're welcome to contribute. Open an issue or a PR.

## License

This project is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.gnu.org/licenses/agpl-3.0.html).

Why AGPL? Because if someone uses this code to offer a service, they must share their modifications. Congressional transparency deserves a project that is also transparent.
