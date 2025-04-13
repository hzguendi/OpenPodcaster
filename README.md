# Podcast Generator

A powerful, configurable tool for automatically generating educational podcasts on any subject. This project creates conversational, engaging podcasts featuring a host, an expert, and a beginner discussing the specified topic.

## 🎙️ Features

- **End-to-End Podcast Creation**: From subject to audio file in a single command
- **Four-Step Pipeline**:
  1. Research generation using LLMs
  2. Transcript creation
  3. Text-to-speech conversion
  4. Final podcast assembly
- **Token Streaming Support**:
  - Real-time display of generated tokens in progress bars
  - Visual feedback during AI generation processes
  - Configurable for research and transcript generation
- **Multiple AI Provider Support**:
  - Research/Transcript: Ollama, OpenRouter, DeepSeek
  - TTS: 
    - ElevenLabs (cloud)
    - Gemini (cloud)
    - Coqui (offline/local)
- **Highly Configurable**:
  - Voice characteristics for each speaker
  - Audio quality settings
  - Character limits and model parameters
  - Customizable prompt templates
- **Developer-Friendly**:
  - Colored console output
  - Detailed progress tracking
  - Comprehensive logging
  - Modular architecture

## 📋 Requirements

- Python 3.8-3.12 (Coqui TTS requires Python <3.13)
- FFmpeg installed on your system
- API keys for cloud providers (not needed for Coqui TTS)

### Python 3.13 Compatibility

Python 3.13 removed the built-in `audioop` module that pydub depends on and has incompatibilities with Coqui TTS. The application handles this by:

1. Automatically detecting missing modules and switching to a direct FFmpeg fallback
2. Using simplified audio processing that concatenates files without advanced audio manipulation

If you're using Python 3.13, some advanced audio features (volume normalization, fades) may be limited, but the core functionality will work as long as FFmpeg is installed.

## 🔧 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/podcast_gen.git
   cd podcast_gen
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install FFmpeg (if not already installed):
   - **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
   - **macOS with Homebrew**: `brew install ffmpeg`
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

4. Set up configuration:
   ```bash
   cp .env.example .env
   # Edit .env file with your API keys
   ```

## ⚙️ Configuration

### API Keys

Edit the `.env` file to add your API keys:

```
OLLAMA_API_KEY=your_ollama_key
OPENROUTER_API_KEY=your_openrouter_key
DEEPSEEK_API_KEY=your_deepseek_key
GEMINI_API_KEY=your_gemini_key
ELEVENLABS_API_KEY=your_elevenlabs_key
```

### Main Configuration

The `config/conf.yml` file contains all configurables:

- **Research settings**: Provider, model, temperature, token limits
- **Transcript settings**: Character limits, speaker names
- **TTS settings**: Voice IDs, speaking rates, stability (ElevenLabs, Gemini, Coqui)
- **Audio settings**: Sample rate, bitrate, normalization
- **API timeouts**: Custom timeout values for each provider
- **API endpoints**: URLs for various provider APIs

### Prompt Templates

Customize the prompt templates in `config/prompts/`:
- `research_prompt.txt`: Template for generating research
- `transcript_prompt.txt`: Template for creating the podcast transcript

## 🚀 Usage

Basic usage:

```bash
python main.py "The history and science of coffee"
```

The output will be saved in a timestamped directory:
```
data/YYYY-MM-DD_HH-MM-SS/
├── research.md          # Generated research
├── transcript.txt       # Generated podcast transcript
├── audio_clips/         # Individual audio segments
│   ├── 000_host.mp3
│   ├── 001_expert.mp3
│   └── ...
├── podcast.mp3          # Final assembled podcast
└── processing.log       # Processing log
```

## 🔍 Advanced Usage

### Customizing Speaker Voices

Edit `conf.yml` to change voice settings:

```yaml
tts:
  provider: coqui  # Use local Coqui TTS
  host:
    # Coqui settings
    model: tts_models/en/ljspeech/tacotron2-DDC
    vocoder: vocoder_models/en/ljspeech/hifigan_v2
    language: en
  expert:
    model: tts_models/en/vctk/vits
    speaker: p225  # Specific speaker ID from VCTK dataset
  beginner:
    model: tts_models/multilingual/multi-dataset/your_tts
    language: en
```

### Adding Background Music

Add paths to intro/outro music in `conf.yml`:

```yaml
assembler:
  intro_music: "/path/to/intro_music.mp3"
  outro_music: "/path/to/outro_music.mp3"
```

### Enabling Token Streaming

Enable token streaming in the progress bars for real-time feedback during generation:

```yaml
research:
  stream_tokens: true  # Show incoming tokens in progress bar during research

transcript:
  stream_tokens: true  # Show incoming tokens in progress bar during transcript generation
```

When enabled, you'll see each token as it's generated and the progress bar will show completion against the maximum expected tokens.

### Changing Models

Change the AI models in `conf.yml`:

```yaml
research:
  provider: openrouter
  model: anthropic/claude-3-opus-20240229  # Change to a different model
```

### Configuring API Timeouts

Adjust the timeout values in the `api_timeouts` section of `conf.yml` to handle large requests or slower responses from API providers:

```yaml
api_timeouts:
  ollama_research: 300   # 5 minutes for research generation with Ollama
  ollama_transcript: 600  # 10 minutes for transcript generation with Ollama
  openrouter: 180        # 3 minutes for OpenRouter requests
  deepseek: 180          # 3 minutes for DeepSeek requests
  elevenlabs: 60         # 1 minute for ElevenLabs TTS requests
```

For local Ollama models, especially larger ones, you may need to increase timeouts significantly to allow for loading the model and generating lengthy content.

## 📁 Project Structure

```
podcast_gen/
├── config/
│   ├── conf.yml                   # Main configuration
│   └── prompts/                   # Prompt templates
│       ├── research_prompt.txt
│       └── transcript_prompt.txt
├── data/                          # Output directory
├── src/
│   ├── research.py                # Research generation
│   ├── transcript.py              # Transcript generation
│   ├── tts.py                     # Text-to-speech conversion
│   ├── assembler.py               # Audio assembly
│   └── utils/                     # Utility modules
│       ├── config_loader.py
│       ├── file_utils.py
│       ├── logging_utils.py
│       └── progress.py
├── .env.example                   # Environment variables template
├── main.py                        # Entry point
└── requirements.txt               # Dependencies
```

## ❓ Troubleshooting

### API Connection Issues
- Check your API keys in `.env`
- Verify internet connection
- Ensure API endpoints in `conf.yml` are correct

### Audio Processing Problems
- Verify FFmpeg is installed correctly
- Check file permissions
- Ensure output directories are writable

### API Timeout Issues
- If experiencing timeout errors with Ollama or other providers, adjust the timeout values in the `api_timeouts` section of `conf.yml`
- For large models or complex requests, consider increasing timeouts significantly

### Memory Issues
- Reduce character limits in `conf.yml`
- Use smaller/more efficient models
- Reduce audio quality settings

## 📝 Logging

Logs are saved in:
- Console (with color coding)
- `data/YYYY-MM-DD_HH-MM-SS/processing.log`

Adjust log level in `conf.yml`:
```yaml
logging:
  level: DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- ElevenLabs for TTS capabilities
- Google Gemini for TTS capabilities
- Various LLM providers for research and transcript generation
