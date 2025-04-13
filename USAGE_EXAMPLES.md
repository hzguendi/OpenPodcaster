# OpenPodcaster - Usage Examples

This document provides detailed examples of how to use OpenPodcaster in different scenarios, from basic usage to advanced configurations.

## Table of Contents

- [Getting Started](#getting-started)
- [Basic Usage Examples](#basic-usage-examples)
- [Configuration Examples](#configuration-examples)
- [Provider-Specific Examples](#provider-specific-examples)
- [Voice & Audio Customization](#voice--audio-customization)
- [Output Optimization](#output-optimization)
- [Workflow Examples](#workflow-examples)
- [Troubleshooting Examples](#troubleshooting-examples)

## Getting Started

### First Run

After installation, generate your first podcast:

```bash
python main.py "Introduction to quantum computing"
```

This will create a podcast using your default configuration.

### Understanding Output

After running OpenPodcaster, you'll find your generated podcast in a timestamped directory:

```
data/2025-04-13_15-30-45/
├── research.md          # AI-generated research
├── transcript.txt       # Generated podcast script
├── audio_clips/         # Individual speaker audio clips
│   ├── 000_host.mp3     # Host introduction
│   ├── 001_expert.mp3   # Expert's first response
│   └── ...              # Additional clips
├── podcast.mp3          # Final assembled podcast
└── processing.log       # Detailed processing log
```

## Basic Usage Examples

### Simple Subject Examples

```bash
# Historical topic
python main.py "The rise and fall of the Roman Empire"

# Scientific topic
python main.py "How photosynthesis works"

# Technology topic
python main.py "The evolution of artificial intelligence"

# Cultural topic
python main.py "The history and influence of jazz music"
```

### Specific Focus Examples

For more targeted content, be specific with your topic:

```bash
# Instead of:
python main.py "Climate change"

# Be more specific:
python main.py "The impact of climate change on ocean ecosystems"
```

### Viewing Progress

Watch token-by-token generation in real-time:

```bash
# First enable token streaming in conf.yml:
# research:
#   stream_tokens: true
# transcript:
#   stream_tokens: true

python main.py "The science of black holes"
```

## Configuration Examples

### Changing Speaker Names

Customize the speaker names in your podcast:

```yaml
# In conf.yml
transcript:
  host_name: SARAH
  expert_name: DR_JENKINS
  beginner_name: ALEX
```

Then run:

```bash
python main.py "The human immune system"
```

### Setting Character Limits

Control podcast length by adjusting character limits:

```yaml
# In conf.yml - Shorter podcast
research:
  character_limit: 6000  # Reduced from default 8000

transcript:
  character_limit: 6000  # Reduced from default 8000

# OR in conf.yml - Longer, more detailed podcast
research:
  character_limit: 10000  # Increased from default

transcript:
  character_limit: 10000  # Increased from default
```

### Changing Temperature Settings

Adjust the "creativity" of the AI:

```yaml
# In conf.yml - More factual, consistent
research:
  temperature: 0.3  # Lower temperature for factual content

# In conf.yml - More creative, varied
transcript:
  temperature: 0.9  # Higher temperature for engaging dialogue
```

## Provider-Specific Examples

### Using Ollama (Local LLM)

```yaml
# In conf.yml
research:
  provider: ollama
  model: llama3  # Or another local model
  
transcript:
  provider: ollama
  model: mistral  # Can use different models for each component
```

Make sure Ollama is running:

```bash
# Start Ollama service if not running
ollama serve

# Check available models
ollama list

# Run OpenPodcaster
python main.py "The basics of machine learning"
```

### Using OpenRouter with Specific Models

```yaml
# In .env
OPENROUTER_API_KEY=your_api_key_here

# In conf.yml
research:
  provider: openrouter
  model: anthropic/claude-3-opus-20240229  # High-quality research

transcript:
  provider: openrouter
  model: anthropic/claude-3-haiku-20240307  # Faster, cheaper for transcript
```

### Using ElevenLabs for Premium Voices

```yaml
# In .env
ELEVENLABS_API_KEY=your_api_key_here

# In conf.yml
tts:
  provider: elevenlabs
  model_id: eleven_multilingual_v2
  
  host:
    voice_id: pNInz6obpgDQGcFmaJgB  # Example voice ID
    stability: 0.5
    similarity_boost: 0.75
```

### Using Coqui for Offline TTS

```yaml
# In conf.yml
tts:
  provider: coqui
  
  coqui_config:
    use_gpu: true  # Speed up processing if GPU available
    
  host:
    model: tts_models/en/vctk/vits
    speaker: p273  # British male speaker
```

## Voice & Audio Customization

### Creating Distinct Character Voices

Configure speakers with unique voice personalities:

```yaml
# In conf.yml
tts:
  # Host: Professional, slightly faster pace
  host:
    # ElevenLabs
    voice_id: pNInz6obpgDQGcFmaJgB
    stability: 0.3  # More variation
    
    # Gemini
    voice_name: en-US-Studio-O
    speaking_rate: 1.1  # Slightly faster
    pitch: 0.0
    
    # Coqui
    model: tts_models/en/vctk/vits
    speaker: p273
    speed: 1.05

  # Expert: Authoritative, deliberate pace
  expert:
    # ElevenLabs
    voice_id: EXAVITQu4vr4xnSDxMaL
    stability: 0.8  # More consistent
    
    # Gemini
    voice_name: en-US-Neural2-D
    speaking_rate: 0.95  # Slightly slower
    pitch: -2.0  # Deeper voice
    
    # Coqui
    model: tts_models/en/vctk/vits
    speaker: p231
    speed: 0.93

  # Beginner: Enthusiastic, casual tone
  beginner:
    # ElevenLabs
    voice_id: yoZ06aMxZJJ28mfd3POQ
    stability: 0.4  # More expressive
    
    # Gemini
    voice_name: en-US-Neural2-F
    speaking_rate: 1.05
    pitch: 3.0  # Higher pitch
    
    # Coqui
    model: tts_models/en/vctk/vits
    speaker: p262
    speed: 1.08
```

### Adding Background Music

```yaml
# In conf.yml
assembler:
  intro_music: "/path/to/intro_music.mp3"
  outro_music: "/path/to/outro_music.mp3"
  
  # Fade settings
  intro_fade_in: 2000  # 2 seconds
  intro_fade_out: 3000  # 3 seconds
  silence_after_intro: 1500  # 1.5 seconds
  
  outro_fade_in: 2500  # 2.5 seconds
  outro_fade_out: 4000  # 4 seconds
  silence_before_outro: 1500  # 1.5 seconds
```

### Adjusting Audio Quality

For high-quality audio:

```yaml
# In conf.yml
assembler:
  sample_rate: 48000  # Higher sample rate
  bitrate: "256k"  # Higher bitrate
  normalize_volume: true
  target_dBFS: -14  # Broadcast standard
```

For smaller file size:

```yaml
# In conf.yml
assembler:
  sample_rate: 22050  # Lower sample rate
  bitrate: "96k"  # Lower bitrate
```

## Output Optimization

### Fine-tuning LLM Parameters

```yaml
# In conf.yml
research:
  temperature: 0.5  # More factual research
  max_tokens: 6000  # More detailed research

transcript:
  temperature: 0.8  # More creative dialogue
  max_tokens: 10000  # Longer podcast
```

### Using Natural Speech Patterns

```yaml
# In conf.yml
tts:
  natural_speech:
    enable_breathing: true    # Add natural breathing pauses
    enable_fillers: true      # Allow um, uh, etc.
    sentence_pause: 0.6       # Pause between sentences
    paragraph_pause: 0.9      # Pause between paragraphs
    emphasis_level: 0.7       # Word emphasis strength
    randomize_pauses: true    # Add variation to pauses
```

## Workflow Examples

### Educational Series

Create a series of educational podcasts on related topics:

```bash
# First create a directory for the series
mkdir -p data/biology_series

# Generate each episode and move to series directory
python main.py "The cell: Basic structure and function"
mv data/$(ls -t data | head -1) data/biology_series/01_cells

python main.py "DNA and RNA: The genetic code"
mv data/$(ls -t data | head -1) data/biology_series/02_dna_rna

python main.py "Proteins: From genes to structure and function"
mv data/$(ls -t data | head -1) data/biology_series/03_proteins
```

### Custom Prompt Workflow

Customize prompts for specialized content:

1. Edit `config/prompts/research_prompt.txt`:
   - Add sections specific to your needs
   - Emphasize aspects important to your topic

2. Edit `config/prompts/transcript_prompt.txt`:
   - Modify podcast structure
   - Adjust speaking style guidance

3. Run OpenPodcaster with your customized prompts:
   ```bash
   python main.py "Your specialized topic"
   ```

### Full Offline Mode

For privacy or no-internet situations:

1. Install Ollama and download models:
   ```bash
   ollama pull llama3
   ```

2. Configure for all-local processing:
   ```yaml
   # In conf.yml
   research:
     provider: ollama
     model: llama3
   
   transcript:
     provider: ollama
     model: llama3
   
   tts:
     provider: coqui
   ```

3. Generate your podcast:
   ```bash
   python main.py "Your topic here"
   ```

## Troubleshooting Examples

### API Timeout Issues

If experiencing timeouts with large models:

```yaml
# In conf.yml
api_timeouts:
  ollama_research: 600  # 10 minutes (up from 5)
  ollama_transcript: 900  # 15 minutes (up from 10)
  openrouter: 300  # 5 minutes (up from 3)
```

### Memory Issues with Local Models

For Ollama with larger models:

```bash
# Launch Ollama with more GPU memory
OLLAMA_GPU_LAYERS=43 ollama serve

# Or with specific VRAM allocation (MB)
OLLAMA_GPU_VRAM=8192 ollama serve
```

### Handling Long Topics

For very complex subjects that need more detail:

```yaml
# In conf.yml - Increase all limits
research:
  max_tokens: 8000  # Double default
  character_limit: 16000  # Double default

transcript:
  max_tokens: 8000  # Double default
  character_limit: 16000  # Double default
```

Then break into parts:

```bash
# Generate a multi-part podcast
python main.py "The complete history of quantum mechanics - Part 1: Early discoveries"
python main.py "The complete history of quantum mechanics - Part 2: Modern developments"
```

### Sample Output Structure

Here's the typical structure of a generated transcript:

```
[00:00:00] INTRODUCTION
HOST: Welcome to our podcast! Today we're exploring the fascinating world of quantum computing with our expert, Dr. Jenkins, and our curious beginner, Alex.

EXPERT: Thank you for having me, Sarah. I'm excited to break down this complex topic.

BEGINNER: I've heard quantum computing mentioned a lot lately, but I honestly have no idea what makes it different from the laptop I'm using right now.

---

[00:01:30] BACKGROUND & CONTEXT
HOST: That's a great place to start, Alex. Dr. Jenkins, could you give us some context about traditional computing before we dive into quantum?

EXPERT: Absolutely. The computers we use today operate using bits - essentially switches that can be either 0 or 1...

... (continues)
```

This structured format ensures an engaging, educational conversation that flows naturally and covers the topic comprehensively.