# OpenPodcaster

<div align="center">

**AI-Powered Educational Podcast Generator**

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![FFmpeg Required](https://img.shields.io/badge/requires-FFmpeg-red.svg)](https://ffmpeg.org/)

</div>

## 🎙️ Overview

OpenPodcaster is a powerful, configurable tool for automatically generating educational podcasts on any subject. With a single command, it creates engaging, conversational podcasts featuring a host, an expert, and a beginner discussing your chosen topic. Perfect for educators, content creators, and anyone looking to produce professional-quality educational audio content without extensive production resources.

## ✨ Key Features

### End-to-End Podcast Creation
- **Single Command Generation**: From topic to complete podcast in one step
- **Smart Pipeline**: Research → Transcript → Speech → Assembly
- **Dynamic Content**: Unique, educational content tailored to any subject

### Multiple AI Provider Support
- **Research & Transcript Generation**:
  - 🤖 **Local**: Ollama (run models on your own hardware)
  - ☁️ **Cloud**: OpenRouter, DeepSeek (access powerful cloud models)
- **Text-to-Speech**:
  - 🎤 **ElevenLabs**: Premium studio-quality voices
  - 🔊 **Gemini**: Google's advanced TTS technology
  - 💻 **Coqui**: Offline local TTS (no API key needed)

### Interactive Experience
- **Token Streaming**: Watch content generation in real-time
- **Progress Visualization**: Clear progress indicators for each step
- **Detailed Logging**: Comprehensive logs for troubleshooting

### High Customization
- **Voice Personalization**: Configure unique voices for each speaker
- **Audio Engineering**: Control audio quality, effects, and mixing
- **Content Control**: Set research depth and podcast length
- **Custom Prompts**: Design your own prompt templates

## 📋 Requirements

- **Python**: 3.8-3.12 recommended
- **FFmpeg**: Required for audio processing
- **API Keys**: For cloud services (not needed for local-only usage)

## 🔧 Installation

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/OpenPodcaster.git
cd OpenPodcaster

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp .env.example .env
# Edit .env file with your API keys
```

### Platform-Specific FFmpeg Installation

<details>
<summary>📌 Ubuntu/Debian</summary>

```bash
sudo apt update
sudo apt install ffmpeg
```
</details>

<details>
<summary>📌 macOS</summary>

```bash
# With Homebrew
brew install ffmpeg

# With MacPorts
port install ffmpeg
```
</details>

<details>
<summary>📌 Windows</summary>

1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Add to your PATH environment variable
3. Or use package managers:
   ```
   winget install ffmpeg
   # or
   choco install ffmpeg
   ```
</details>

## 🚀 Quick Usage

Generate your first podcast with a single command:

```bash
python main.py "The history and science of coffee"
```

Your podcast will be created in a timestamped directory:

```
data/YYYY-MM-DD_HH-MM-SS/
├── research.md          # Generated research
├── transcript.txt       # Generated podcast transcript
├── audio_clips/         # Individual audio segments
├── podcast.mp3          # Final assembled podcast
└── processing.log       # Processing log
```

## 🔍 Configuration

OpenPodcaster is highly configurable through two main files:

1. **`.env`**: For API keys and critical overrides
2. **`config/conf.yml`**: For detailed application settings

<details>
<summary>📝 Essential .env Configuration</summary>

```
# Add your API keys here
OPENROUTER_API_KEY=your_openrouter_key
ELEVENLABS_API_KEY=your_elevenlabs_key

# Optional overrides
RESEARCH_MODEL=anthropic/claude-3-opus-20240229
TTS_PROVIDER=elevenlabs
```
</details>

<details>
<summary>📝 Core conf.yml Settings</summary>

```yaml
# Key sections include:
research:
  provider: openrouter
  model: anthropic/claude-3-opus-20240229
  temperature: 0.7

transcript:
  host_name: HOST
  expert_name: EXPERT
  beginner_name: BEGINNER

tts:
  provider: elevenlabs
  host:
    voice_id: pNInz6obpgDQGcFmaJgB
    stability: 0.5

assembler:
  intro_music: "/path/to/music.mp3"
  normalize_volume: true
```

See [CONFIGURATION.md](CONFIGURATION.md) for complete documentation.
</details>

## 📊 Project Structure

```
OpenPodcaster/
├── config/                      # Configuration files
│   ├── conf.yml                 # Main config
│   └── prompts/                 # Prompt templates
│       ├── research_prompt.txt
│       └── transcript_prompt.txt
├── data/                        # Output directory
├── src/                         # Source code
│   ├── research.py              # Research generation
│   ├── transcript.py            # Transcript creation
│   ├── tts.py                   # Text-to-speech
│   ├── assembler.py             # Audio assembly
│   └── utils/                   # Utility modules
├── .env                         # Environment variables
├── main.py                      # Entry point
└── requirements.txt             # Dependencies
```

## 🛠️ Advanced Usage

OpenPodcaster offers extensive customization for advanced users. See [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) for detailed examples including:

- Using different AI models for research and transcripts
- Customizing voice characteristics for each speaker
- Adding background music and sound effects
- Optimizing output quality and file size
- Using offline providers for complete privacy

## 📝 Logging and Troubleshooting

OpenPodcaster provides comprehensive logging:

- **Console Output**: Color-coded for easy reading
- **Log Files**: Detailed logs stored with each podcast
- **Configurable Level**: Set verbosity in `conf.yml`

For common issues and solutions, see the [Troubleshooting](#troubleshooting) section below.

## ❓ Troubleshooting

<details>
<summary>🔍 API Connection Issues</summary>

- Verify API keys in `.env`
- Check internet connectivity
- Confirm API endpoints in `conf.yml`
- For Ollama: ensure Ollama service is running locally
</details>

<details>
<summary>🔍 Audio Processing Problems</summary>

- Verify FFmpeg is installed and accessible
- Check file permissions for output directories
- For Python 3.13+: some audio features will be limited
</details>

<details>
<summary>🔍 Memory and Performance Issues</summary>

- Reduce model sizes in `conf.yml`
- Lower character limits for research and transcript
- For local models: ensure adequate system resources
</details>

<details>
<summary>🔍 Timeout Errors</summary>

- Increase timeout values in `api_timeouts` section of `conf.yml`
- Consider using smaller models for faster generation
- Verify API provider status
</details>

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- Thanks to the various LLM and TTS providers for their APIs
- FFmpeg for audio processing capabilities
- The open-source community for invaluable tools and libraries