# Digital Twin Test Case Generation & Logging Guide

This guide explains how to use the new digital twin simulation capabilities for generating realistic test cases and comprehensive defect logging.

## Overview

The mTrac SP system now includes a complete digital twin simulation environment that can:

- **Generate realistic test cases** with various defect scenarios
- **Log detailed inspection data** with comprehensive metrics
- **Track performance** across multiple inspection sessions
- **Provide analytics** for AI inspection quality

## Features

### 🧪 Test Case Generation

#### Defect Types
The system can generate 8 different types of defects:
- **Missing Component**: Component completely absent from board
- **Misaligned**: Component positioned incorrectly
- **Solder Defect**: Poor solder joint quality or bridges
- **Damage**: Physical damage to components
- **Contamination**: Foreign material on board
- **Wrong Component**: Incorrect component installed
- **Orientation Error**: Polarized components installed backwards
- **Size Variation**: Component size outside specifications

#### Severity Levels
- **Critical**: Board non-functional, safety risk
- **Major**: Performance issues, likely failure
- **Minor**: Quality issues, may affect reliability
- **Cosmetic**: Visual defects only

#### Difficulty Levels
- **Easy**: Simple layouts, obvious defects
- **Medium**: Complex layouts, moderate detection difficulty
- **Hard**: Dense layouts, subtle defects

### 📊 Digital Twin Logging

#### Session Metrics
- **Defect Detection Rate**: Percentage of actual defects found
- **False Positive Rate**: Percentage of good components flagged as defective
- **Inspection Time**: Average time per component
- **AI Performance**: Accuracy, precision, recall, F1-score
- **Cost Analysis**: Estimated cost per inspection

#### Detailed Logging
- **Component-level tracking**: Each inspection event logged
- **AI Decision Logging**: Raw AI responses and reasoning
- **Performance Analytics**: Detection rates by defect type and severity
- **Timeline Analysis**: Inspection sequence and timing

## Usage Guide

### 1. Generate Test Cases

#### Via UI
1. Open the web interface
2. In the "Digital Twin Test Cases" section
3. Click "Generate Test Case"
4. Review the generated test case details
5. Click "Load Test Case" to start inspection

#### Via API
```bash
# Generate a test case
curl -X POST http://localhost:8000/generate_test_case \
  -H "Content-Type: application/json" \
  -d '{
    "defect_rate": 0.15,
    "difficulty_level": "medium",
    "num_components": 20
  }'

# Load the test case
curl -X POST http://localhost:8000/load_test_case \
  -H "Content-Type: application/json" \
  -d '{"test_case_data": ...}'
```

### 2. Run Inspection Sessions

1. **Enable AI Mode**: Click "Toggle AI/MANUAL" to switch to AI mode
2. **Start Inspection**: The AI will automatically begin inspecting components
3. **Monitor Progress**: Watch real-time statistics and AI decisions
4. **Session Completion**: Click "End Session" when inspection is complete

### 3. Review Results

#### Session Metrics
After ending a session, you'll see:
- **Detection Rate**: How well the AI found actual defects
- **False Positives**: How many good components were incorrectly flagged
- **Average Time**: Time spent per component
- **Total Components**: Number of components inspected

#### Detailed Reports
Each session generates:
- **CSV Logs**: `inspection_events.csv`, `inspection_sessions.csv`
- **JSON Reports**: `session_report_[session_id].json`
- **Performance Metrics**: `performance_metrics.csv`

## Advanced Configuration

### Custom Test Case Generation

#### Programmatic Generation
```python
from backend.sim.test_generator import TestCaseGenerator

generator = TestCaseGenerator(seed=42)
test_case = generator.generate_test_case(
    board_width=400,
    board_height=300,
    num_components=25,
    defect_rate=0.20,
    difficulty_level="hard"
)
```

#### Test Suite Generation
```python
test_suite = generator.generate_test_suite(
    num_cases=10,
    variations=[
        {"defect_rate": 0.05, "difficulty_level": "easy"},
        {"defect_rate": 0.15, "difficulty_level": "medium"},
        {"defect_rate": 0.25, "difficulty_level": "hard"}
    ]
)
```

### Export/Import Test Cases

#### Export Test Case
```python
generator.export_test_case(test_case, "my_test_case.json")
```

#### Import Test Case
```python
imported_case = generator.import_test_case("my_test_case.json")
```

## Performance Analytics

### Detection by Defect Type
The system tracks how well the AI detects different types of defects:
```json
{
  "missing_component": {
    "detection_rate": 0.95,
    "total": 5,
    "detected": 4
  },
  "solder_defect": {
    "detection_rate": 0.80,
    "total": 4,
    "detected": 3
  }
}
```

### Detection by Severity
```json
{
  "critical": {
    "detection_rate": 0.98,
    "total": 2,
    "detected": 2
  },
  "minor": {
    "detection_rate": 0.75,
    "total": 8,
    "detected": 6
  }
}
```

### Cost Analysis
The system estimates inspection costs based on AI provider:
- **Gemini**: ~$0.005 per inspection session
- **OpenAI**: ~$0.01 per inspection session  
- **Anthropic**: ~$0.02 per inspection session

## File Structure

```
logs/
├── inspection_events.csv          # Individual inspection events
├── inspection_sessions.csv        # Session summaries
├── performance_metrics.csv        # Performance analytics
└── session_report_[ID].json      # Detailed session reports
```

## Best Practices

### Test Case Design
1. **Vary Defect Rates**: Test with 5%, 15%, and 25% defect rates
2. **Mix Difficulty Levels**: Include easy, medium, and hard cases
3. **Realistic Scenarios**: Use defect types common in your industry
4. **Consistent Evaluation**: Use the same test cases for comparison

### Session Management
1. **Clear Sessions**: Always end sessions properly to save data
2. **Monitor Performance**: Watch detection rates in real-time
3. **Review Logs**: Check detailed logs for improvement opportunities
4. **Track Trends**: Monitor performance over multiple sessions

### AI Optimization
1. **Prompt Engineering**: Adjust AI prompts for better defect detection
2. **Model Selection**: Choose the best AI model for your use case
3. **Cost Management**: Monitor API usage and costs
4. **Quality Assurance**: Validate AI decisions against ground truth

## Troubleshooting

### Common Issues

#### Test Case Generation Fails
- Check backend logs for errors
- Verify all dependencies are installed
- Ensure sufficient system resources

#### Session Not Recording
- Verify the digital twin logger is initialized
- Check file permissions for logs directory
- Ensure test case is properly loaded

#### Poor Detection Rates
- Review AI prompts and system messages
- Check defect difficulty settings
- Verify vision system configuration

#### High False Positives
- Adjust AI confidence thresholds
- Review defect classification criteria
- Check component quality standards

### Debug Information

Enable debug logging by setting environment variable:
```bash
export DEBUG=true
python server.py
```

## API Reference

### Test Case Endpoints

#### GET /test_case_result
Returns the result of the last test case generation.

#### GET /load_result  
Returns the result of the last test case load operation.

#### GET /session_result
Returns metrics from the last completed session.

#### GET /current_test_case
Returns information about the currently loaded test case.

#### GET /history_result
Returns session history and performance summary.

### Control Messages

#### generate_test_case
```json
{
  "type": "generate_test_case",
  "board_width": 400,
  "board_height": 300,
  "num_components": 20,
  "defect_rate": 0.15,
  "difficulty_level": "medium"
}
```

#### load_test_case
```json
{
  "type": "load_test_case",
  "test_case_data": {...}
}
```

#### end_test_session
```json
{
  "type": "end_test_session"
}
```

## Integration Examples

### Automated Testing Pipeline
```python
# Generate test suite
generator = TestCaseGenerator()
test_suite = generator.generate_test_suite(num_cases=50)

# Run automated inspection
for test_case in test_suite:
    # Load test case
    runtime.load_test_case({"test_case_data": test_case})
    
    # Run inspection (wait for completion)
    # ... inspection logic ...
    
    # End session and collect metrics
    metrics = runtime.end_test_session()
    
    # Analyze results
    analyze_performance(metrics)
```

### Performance Benchmarking
```python
# Compare AI providers
providers = ["openai", "anthropic", "gemini"]
results = {}

for provider in providers:
    os.environ["LLM_PROVIDER"] = provider
    
    # Run standardized test suite
    metrics = run_test_suite(standard_test_cases)
    results[provider] = metrics

# Generate comparison report
generate_comparison_report(results)
```

This digital twin system provides a comprehensive platform for testing, validating, and optimizing AI-powered PCBA inspection systems.
