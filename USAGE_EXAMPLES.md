# Podcast Generator - Usage Examples

This document provides detailed examples of how to use the Podcast Generator tool in different scenarios.

## Table of Contents
- [Basic Examples](#basic-examples)
- [Customization Examples](#customization-examples)
- [Provider-Specific Examples](#provider-specific-examples)
- [Voice Customization](#voice-customization)
- [Advanced Audio Configuration](#advanced-audio-configuration)
- [Optimizing Output Quality](#optimizing-output-quality)

## Basic Examples

### Generating a Simple Podcast

The most basic usage is to generate a podcast on a specific subject:

```bash
python main.py "The history of artificial intelligence"
```

This will:
1. Generate research on AI history
2. Create a transcript with default speakers
3. Convert to speech using the default TTS provider
4. Assemble the final podcast

### Using a Detailed Subject Description

For more focused content, provide a more detailed subject:

```bash
python main.py "The environmental impact of fast fashion and sustainable alternatives"
```

### Viewing the Logs During Processing

Watch the progress in real-time:

```bash
# Set log level to DEBUG in conf.yml first
python main.py "Quantum computing explained for beginners"
```

## Customization Examples

### Changing Speaker Names

Edit `conf.yml` to customize speaker names:

```yaml
transcript:
  host_name: SARAH
  expert_name: PROFESSOR
  beginner_name: STUDENT
```

Then run:

```bash
python main.py "The science of climate change"
```

### Customizing the Prompts

To focus on specific aspects of a topic, edit the prompt templates:

1. Modify `config/prompts/research_prompt.txt` to request more historical context
2. Run the generator:
   ```bash
   python main.py "The evolution of smartphones"
   ```

### Setting Character Limits

For shorter or longer podcasts, adjust the character limits:

```yaml
# In conf.yml
research:
  character_limit: 5000  # Shorter research

transcript:
  character_limit: 8000  # Shorter transcript
```

## Provider-Specific Examples

### Using Ollama (Local LLM)

Configure for using Ollama:

```yaml
# In conf.yml
research:
  provider: ollama
  model: llama3  # Or your preferred local model

transcript:
  provider: ollama
  model: llama3
```

Then run:

```bash
python main.py "The basics of machine learning"
```

### Using OpenRouter with Specific Models

For specialized content, pick specific models:

```yaml
# In conf.yml
research:
  provider: openrouter
  model: anthropic/claude-3-opus-20240229

transcript:
  provider: openrouter
  model: google/gemini-pro
```

### Using ElevenLabs for High-Quality Voices

For premium voice quality:

```yaml
# In conf.yml
tts:
  provider: elevenlabs
  model_id: eleven_multilingual_v2
```

Make sure your ElevenLabs API key is in `.env`.

## Voice Customization

### Creating Distinct Character Voices

Configure each speaker with a distinct voice personality:

```yaml
# In conf.yml
tts:
  host:
    # ElevenLabs
    voice_id: pNInz6obpgDQGcFmaJgB
    stability: 0.3  # Lower stability for more variation
    similarity_boost: 0.7
    
    # Gemini
    voice_name: en-US-Studio-O
    speaking_rate: 1.1  # Slightly faster
    pitch: 0.0

  expert:
    # ElevenLabs
    voice_id: EXAVITQu4vr4xnSDxMaL
    stability: 0.8  # Higher stability for authority
    similarity_boost: 0.8
    
    # Gemini
    voice_name: en-US-Neural2-D
    speaking_rate: 0.95  # Slightly slower
    pitch: -2.0  # Deeper voice

  beginner:
    # ElevenLabs
    voice_id: yoZ06aMxZJJ28mfd3POQ
    stability: 0.4
    similarity_boost: 0.7
    
    # Gemini
    voice_name: en-US-Neural2-F
    speaking_rate: 1.05
    pitch: 3.0  # Higher pitch
```

### Testing Different Voices

To experiment with different voices:

1. Find voice IDs from your ElevenLabs account or Gemini documentation
2. Update the `conf.yml` file
3. Run the generator with a short subject to test:
   ```bash
   python main.py "A brief history of jazz"
   ```

## Advanced Audio Configuration

### Adding Background Music

Configure intro and outro music:

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

For higher quality audio:

```yaml
# In conf.yml
assembler:
  sample_rate: 48000  # Higher sample rate
  bitrate: "256k"  # Higher bitrate
  normalize_volume: true
  target_dBFS: -14  # Slightly louder
```

For smaller file size:

```yaml
# In conf.yml
assembler:
  sample_rate: 22050  # Lower sample rate
  bitrate: "128k"  # Lower bitrate
```

## Optimizing Output Quality

### Fine-tuning LLM Parameters

Adjust temperature and other parameters for better results:

```yaml
# In conf.yml
research:
  temperature: 0.5  # Lower temperature for more factual research
  max_tokens: 6000  # More tokens for more detailed research

transcript:
  temperature: 0.8  # Higher temperature for more creative dialogue
  max_tokens: 10000  # More tokens for longer podcast
```

### Example Topic Categories

#### Educational Topics
```bash
python main.py "How photosynthesis works"
python main.py "The human immune system explained"
python main.py "Understanding black holes and dark matter"
```

#### Historical Topics
```bash
python main.py "The rise and fall of ancient Rome"
python main.py "The history of aviation"
python main.py "The Manhattan Project and nuclear age"
```

#### Technology Topics
```bash
python main.py "Blockchain technology explained"
python main.py "The evolution of artificial intelligence"
python main.py "How the internet works"
```

#### Cultural Topics
```bash
python main.py "The history of jazz music"
python main.py "The influence of Greek mythology in modern culture"
python main.py "Traditional cuisines from around the world"
```

#### Health Topics
```bash
python main.py "The science of sleep and dreams"
python main.py "Nutrition basics and misconceptions"
python main.py "Understanding mental health"
```

## Example Output Structure

After running the generator, you'll get a directory structure like:

```
data/2025-04-12_15-30-45/
├── research.md
│   # Contains comprehensive research on the topic
│
├── transcript.txt
│   # Example:
│   # HOST: Welcome to our podcast! Today we're discussing...
│   # EXPERT: Thank you for having me. This topic is fascinating because...
│   # BEGINNER: I've always wondered about...
│
├── audio_clips/
│   ├── 000_host.mp3     # Introduction
│   ├── 001_expert.mp3   # Expert's first response
│   ├── 002_beginner.mp3 # Beginner's question
│   └── ...              # More speech segments
│
├── podcast.mp3          # Final assembled podcast
└── processing.log       # Detailed log of the generation process
```
