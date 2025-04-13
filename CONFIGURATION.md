# OpenPodcaster Configuration Guide

This document provides detailed instructions for configuring OpenPodcaster to suit your specific needs. The configuration is split between two main files:

1. **`.env`**: For API keys and environment-specific settings
2. **`config/conf.yml`**: For detailed application configuration

## Table of Contents

- [Environment Variables (.env)](#environment-variables-env)
- [Main Configuration (conf.yml)](#main-configuration-confyml)
  - [Logging](#logging)
  - [Research Generation](#research-generation)
  - [Transcript Generation](#transcript-generation)
  - [Text-to-Speech (TTS)](#text-to-speech-tts)
  - [Audio Assembly](#audio-assembly)
  - [API URLs](#api-urls)
  - [API Timeouts](#api-timeouts)
  - [API Statistics Tracking](#api-statistics-tracking)
- [Prompt Templates](#prompt-templates)
- [Example Configurations](#example-configurations)
  - [Local-Only Setup](#local-only-setup)
  - [Cloud-Based Premium Setup](#cloud-based-premium-setup)
  - [Hybrid Configuration](#hybrid-configuration)

## Environment Variables (.env)

The `.env` file stores sensitive API keys and optional configuration overrides.

### API Keys

```
# LLM Providers for Research and Transcript Generation
OLLAMA_API_KEY=               # Optional: For Ollama if using auth (rarely needed)
OPENROUTER_API_KEY=your_key   # Required for OpenRouter
DEEPSEEK_API_KEY=your_key     # Required for DeepSeek

# TTS Providers
GEMINI_API_KEY=your_key       # Required for Gemini TTS
ELEVENLABS_API_KEY=your_key   # Required for ElevenLabs TTS
```

### Optional Overrides

You can override key configuration settings directly in `.env`:

```
# Optional: Override research provider/model
RESEARCH_PROVIDER=openrouter
RESEARCH_MODEL=anthropic/claude-3-opus-20240229

# Optional: Override transcript provider/model
TRANSCRIPT_PROVIDER=openrouter
TRANSCRIPT_MODEL=anthropic/claude-3-sonnet-20240229

# Optional: Override TTS provider
TTS_PROVIDER=elevenlabs
```

> **Note**: Settings in `.env` take precedence over `conf.yml`

## Main Configuration (conf.yml)

The `conf.yml` file in the `config` directory contains all application settings organized by component.

### Logging

Control logging behavior:

```yaml
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  console_output: true  # Enable/disable console output
  file_output: true     # Enable/disable file output
```

### Research Generation

Configure how research content is generated:

```yaml
research:
  provider: ollama  # ollama, openrouter, deepseek
  model: gemma3:1b  # Model name (provider-specific)
  temperature: 0.7  # Creativity level (0.0-1.0)
  max_tokens: 4000  # Maximum output tokens
  character_limit: 8000  # Maximum characters
  stream_tokens: true  # Show real-time token generation
```

Provider-specific model examples:
- **Ollama**: `llama3`, `mistral`, `gemma3:1b`
- **OpenRouter**: `anthropic/claude-3-opus-20240229`, `google/gemini-1.5-pro`
- **DeepSeek**: `deepseek-chat`, `deepseek-coder`

### Transcript Generation

Configure transcript generation and speaker naming:

```yaml
transcript:
  provider: ollama  # ollama, openrouter, deepseek
  model: gemma3:1b  # Model name (provider-specific)
  temperature: 0.8  # Slightly higher for creative dialogue
  max_tokens: 4000  # Maximum output tokens
  character_limit: 8000  # Maximum characters
  stream_tokens: true  # Show real-time token generation
  
  # Speaker names in the transcript
  host_name: HOST  # Default host name
  expert_name: EXPERT  # Default expert name
  beginner_name: BEGINNER  # Default beginner name
```

### Text-to-Speech (TTS)

Configure text-to-speech settings:

```yaml
tts:
  provider: coqui  # elevenlabs, gemini, coqui
  
  # For ElevenLabs
  model_id: eleven_multilingual_v2
  
  # Coqui specific settings
  coqui_config:
    suppress_cli_output: true  # Hide Coqui console output
    use_gpu: auto  # auto, true, false
    progress_bar: true  # Show progress
  
  # Natural speech settings (all providers)
  natural_speech:
    enable_breathing: true  # Add breathing pauses
    enable_fillers: true  # Allow um, uh, etc.
    sentence_pause: 0.6  # Pause between sentences (seconds)
    paragraph_pause: 0.9  # Pause between paragraphs (seconds)
    emphasis_level: 0.7  # Word emphasis strength
    randomize_pauses: true  # Add variation to pauses
```

#### Speaker Voice Configuration

Each speaker can have custom voice settings:

```yaml
tts:
  # ... (other settings)
  
  # Host voice settings
  host:
    # ElevenLabs settings
    voice_id: pNInz6obpgDQGcFmaJgB  # Adam voice
    stability: 0.5  # 0.0-1.0 (higher = more consistent)
    similarity_boost: 0.75  # 0.0-1.0 (higher = closer to original)
    
    # Gemini settings
    voice_name: en-US-Studio-O
    language_code: en-US
    gender: MALE
    speaking_rate: 1.0  # 0.25-4.0
    pitch: 0.0  # -20.0-20.0

    # Coqui settings
    model: tts_models/en/vctk/vits
    speaker: p273  # Speaker ID
    speed: 1.05  # Speech speed
    style: default  # Speaking style
    emotion_strength: 0.65  # Emotion intensity
```

Similar configuration blocks exist for `expert` and `beginner` voices.

### Audio Assembly

Configure the final podcast assembly:

```yaml
assembler:
  # Audio quality settings
  sample_rate: 44100  # Hz
  bitrate: "128k"  # Audio bitrate
  normalize_volume: true  # Normalize audio levels
  target_dBFS: -16  # Target volume level (dB)
  
  # Background music
  intro_music: "/path/to/intro.mp3"  # Optional intro music
  outro_music: "/path/to/outro.mp3"  # Optional outro music
  
  # Music fade settings (milliseconds)
  intro_fade_in: 1000
  intro_fade_out: 2000
  silence_after_intro: 1000
  outro_fade_in: 2000
  outro_fade_out: 5000
  silence_before_outro: 1000
```

### API URLs

Configure API endpoints:

```yaml
api_urls:
  ollama: http://localhost:11434/api/generate
  openrouter: https://openrouter.ai/api/v1/chat/completions
  deepseek: https://api.deepseek.com/v1/chat/completions
  elevenlabs: https://api.elevenlabs.io/v1/text-to-speech
  gemini: https://texttospeech.googleapis.com/v1/text:synthesize
  referer: http://localhost  # HTTP referer for API requests
```

### API Timeouts

Configure timeouts for API calls:

```yaml
api_timeouts:
  ollama_research: 300  # 5 minutes for research
  ollama_transcript: 600  # 10 minutes for transcript
  openrouter: 180  # 3 minutes for OpenRouter calls
  deepseek: 180  # 3 minutes for DeepSeek calls
  elevenlabs: 60  # 1 minute for ElevenLabs calls
```

### API Statistics Tracking

Configure API usage tracking:

```yaml
api_stats:
  enabled: true
  directory: data/api_stats  # Storage directory
  # Retry settings
  max_retries: 3  # Maximum retries for failed requests
  retry_delay: 2  # Base delay between retries (seconds)
  # Alerts
  error_alert_threshold: 5  # Alert after this many errors
```

## Prompt Templates

OpenPodcaster uses template files for generating research and transcripts:

### Research Prompt (`config/prompts/research_prompt.txt`)

This template guides the AI in generating structured research. Key variables:

- `{subject}`: The podcast topic
- `{max_tokens}`: Maximum token limit from config
- `{char_limit}`: Character limit from config

### Transcript Prompt (`config/prompts/transcript_prompt.txt`)

This template guides the AI in creating podcast transcripts. Key variables:

- `{research}`: The generated research content
- `{max_tokens}`: Maximum token limit from config
- `{char_limit}`: Character limit from config
- `{host_name}`, `{expert_name}`, `{beginner_name}`: Speaker names

### Coqui-Specific Prompt (`config/prompts/coqui/transcript_prompt.txt`)

A specialized transcript template with Coqui TTS tags for enhanced speech control:

```xml
<host>Text goes here</host>
<expert>Text goes here</expert>
<beginner>Text goes here</beginner>
<pause sec="0.5" />
<emphasis>important words</emphasis>
<break strength="medium" />
```

## Example Configurations

### Local-Only Setup

For privacy and offline use:

```yaml
# .env
# No API keys needed

# conf.yml
research:
  provider: ollama
  model: llama3

transcript:
  provider: ollama
  model: llama3

tts:
  provider: coqui
  # Coqui voice settings...
```

### Cloud-Based Premium Setup

For highest quality output:

```yaml
# .env
OPENROUTER_API_KEY=your_key
ELEVENLABS_API_KEY=your_key

# conf.yml
research:
  provider: openrouter
  model: anthropic/claude-3-opus-20240229
  temperature: 0.6

transcript:
  provider: openrouter
  model: anthropic/claude-3-sonnet-20240229
  temperature: 0.8

tts:
  provider: elevenlabs
  model_id: eleven_multilingual_v2
  # ElevenLabs voice settings...
```

### Hybrid Configuration

For balanced performance and quality:

```yaml
# .env
ELEVENLABS_API_KEY=your_key

# conf.yml
research:
  provider: ollama
  model: mistral
  temperature: 0.7

transcript:
  provider: ollama
  model: llama3
  temperature: 0.8

tts:
  provider: elevenlabs
  model_id: eleven_multilingual_v2
  # Voice settings...
```

## Finding Voice IDs

### ElevenLabs

To find voice IDs:
1. Log in to [ElevenLabs](https://elevenlabs.io/)
2. Go to Voice Library
3. Select a voice
4. Copy the Voice ID from the URL or settings

### Gemini

Standard voice names:
- `en-US-Studio-O` (male)
- `en-US-Neural2-F` (female)
- `en-US-Neural2-D` (male)
- Full list available in [Google Cloud TTS documentation](https://cloud.google.com/text-to-speech/docs/voices)

### Coqui

For Coqui TTS:
- Standard models: `tts_models/en/ljspeech/tacotron2-DDC`
- VCTK speakers: p225-p376 (e.g., `p273`)
- List available models with: 
  ```bash
  pip install TTS
  tts --list_models
  ```

## Further Resources

- OpenAI's [temperature parameter guide](https://platform.openai.com/docs/api-reference/completions/create#completions/create-temperature)
- [ElevenLabs voice documentation](https://docs.elevenlabs.io/api-reference/voices)
- [Coqui TTS documentation](https://tts.readthedocs.io/)