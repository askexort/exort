# Prompt Engineering Guide

## Techniques

### 1. Role Prompting
"You are a senior Python developer with 15 years of experience..."

### 2. Chain of Thought
"Think step by step. First... Then... Finally..."

### 3. Few-Shot Examples
```
Input: "hello" → Output: "Hello! How can I help?"
Input: "bye" → Output: "Goodbye! Have a great day!"
```

### 4. Output Formatting
"Respond in JSON format with keys: summary, details, confidence"
"Use markdown with headers, bullet points, and code blocks"

### 5. Constraint Setting
"Keep your response under 100 words"
"Only use standard library functions"
"Do not include any explanations"

## Anti-Patterns
- Vague prompts: "Tell me about stuff"
- Conflicting instructions: "Be brief but explain everything in detail"
- Missing context: Assume nothing about what the model knows
