#!/usr/bin/env python3
"""
Digital Twin Demo Script

This script demonstrates the test case generation and digital twin logging capabilities.
Run this script to see a complete example of the digital twin functionality.
"""

import sys
import os
import time
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

from backend.sim.test_generator import TestCaseGenerator, DefectType, DefectSeverity
from backend.sim.digital_twin_logger import DigitalTwinLogger


def demo_test_case_generation():
    """Demonstrate test case generation"""
    print("🧪 Digital Twin Test Case Generation Demo")
    print("=" * 50)
    
    # Initialize the test case generator
    generator = TestCaseGenerator(seed=42)
    
    # Generate different types of test cases
    test_cases = []
    
    print("\n1. Generating Easy Test Case (5% defect rate)")
    easy_case = generator.generate_test_case(
        defect_rate=0.05,
        difficulty_level="easy",
        num_components=15
    )
    test_cases.append(easy_case)
    print(f"   Generated: {easy_case.test_id}")
    print(f"   Components: {len(easy_case.components)}")
    print(f"   Defects: {len(easy_case.defects)}")
    
    print("\n2. Generating Medium Test Case (15% defect rate)")
    medium_case = generator.generate_test_case(
        defect_rate=0.15,
        difficulty_level="medium",
        num_components=20
    )
    test_cases.append(medium_case)
    print(f"   Generated: {medium_case.test_id}")
    print(f"   Components: {len(medium_case.components)}")
    print(f"   Defects: {len(medium_case.defects)}")
    
    print("\n3. Generating Hard Test Case (25% defect rate)")
    hard_case = generator.generate_test_case(
        defect_rate=0.25,
        difficulty_level="hard",
        num_components=25
    )
    test_cases.append(hard_case)
    print(f"   Generated: {hard_case.test_id}")
    print(f"   Components: {len(hard_case.components)}")
    print(f"   Defects: {len(hard_case.defects)}")
    
    # Analyze defect distribution
    print("\n4. Defect Distribution Analysis")
    print("-" * 30)
    
    all_defects = []
    for case in test_cases:
        all_defects.extend(case.defects)
    
    defect_types = {}
    severity_levels = {}
    
    for defect in all_defects:
        defect_type = defect.defect_type.value
        severity = defect.severity.value
        
        defect_types[defect_type] = defect_types.get(defect_type, 0) + 1
        severity_levels[severity] = severity_levels.get(severity, 0) + 1
    
    print("Defect Types:")
    for defect_type, count in defect_types.items():
        print(f"   {defect_type}: {count}")
    
    print("\nSeverity Levels:")
    for severity, count in severity_levels.items():
        print(f"   {severity}: {count}")
    
    return test_cases


def demo_digital_twin_logging(test_cases):
    """Demonstrate digital twin logging"""
    print("\n\n📊 Digital Twin Logging Demo")
    print("=" * 50)
    
    # Initialize the logger
    logger = DigitalTwinLogger()
    
    # Simulate inspection sessions
    for i, test_case in enumerate(test_cases):
        print(f"\n{i+1}. Simulating Inspection Session: {test_case.test_id}")
        print("-" * 40)
        
        # Start session
        session_id = logger.start_session(
            test_case=test_case,
            ai_provider="gemini"
        )
        print(f"   Started session: {session_id}")
        
        # Simulate inspection events
        components_inspected = 0
        defects_found = 0
        
        for component in test_case.components[:10]:  # Simulate first 10 components
            # Determine if this component has a defect
            component_defects = [d for d in test_case.defects if d.component_id == component["component_id"]]
            has_defect = len(component_defects) > 0
            
            # Simulate AI inspection (with some detection difficulty)
            if has_defect:
                defect = component_defects[0]
                # Detection probability based on difficulty
                detection_prob = 1.0 - defect.detection_difficulty
                
                if time.time() % 1 < detection_prob:  # Simulate detection
                    result = "FAIL"
                    defects_found += 1
                    defect_details = {
                        "defect_type": defect.defect_type.value,
                        "severity": defect.severity.value,
                        "description": defect.description
                    }
                else:
                    result = "PASS"  # Missed defect
                    defect_details = None
            else:
                result = "PASS"
                # Small chance of false positive
                if time.time() % 1 < 0.05:  # 5% false positive rate
                    result = "FAIL"
                    defect_details = {"defect_type": "false_positive", "severity": "cosmetic"}
                else:
                    defect_details = None
            
            # Log inspection event
            logger.log_inspection_event(
                component_id=component["component_id"],
                inspection_type="visual",
                result=result,
                confidence=0.85 if result == "PASS" else 0.75,
                ai_decision={"move_to": [component["rect"]["x"], component["rect"]["y"]], "status": "inspecting"},
                gantry_position=(component["rect"]["x"], component["rect"]["y"]),
                inspection_duration=2.0 + (time.time() % 2),  # 2-4 seconds
                defect_details=defect_details
            )
            
            components_inspected += 1
            
            # Simulate inspection time
            time.sleep(0.1)  # Shortened for demo
        
        # End session
        metrics = logger.end_session()
        
        print(f"   Components Inspected: {components_inspected}")
        print(f"   Defects Found: {defects_found}/{len(test_case.defects)}")
        print(f"   Detection Rate: {metrics.defect_detection_rate:.1%}")
        print(f"   False Positive Rate: {metrics.false_positive_rate:.1%}")
        print(f"   Avg Inspection Time: {metrics.average_inspection_time:.2f}s")
        print(f"   Total Session Time: {metrics.total_inspection_time:.1f}s")
    
    # Get performance summary
    print("\n4. Overall Performance Summary")
    print("-" * 35)
    
    summary = logger.get_performance_summary()
    if summary:
        print(f"   Total Sessions: {summary['total_sessions']}")
        print(f"   Average Accuracy: {summary['average_accuracy']:.1%}")
        print(f"   Average Precision: {summary['average_precision']:.1%}")
        print(f"   Average Recall: {summary['average_recall']:.1%}")
        print(f"   Average F1-Score: {summary['average_f1_score']:.1%}")
        print(f"   Average Efficiency: {summary['average_efficiency']:.1f} components/min")
    else:
        print("   No performance data available")


def demo_export_import():
    """Demonstrate test case export/import"""
    print("\n\n💾 Export/Import Demo")
    print("=" * 30)
    
    generator = TestCaseGenerator()
    
    # Generate a test case
    test_case = generator.generate_test_case(
        defect_rate=0.12,
        difficulty_level="medium",
        num_components=18
    )
    
    # Export to file
    export_file = "demo_test_case.json"
    generator.export_test_case(test_case, export_file)
    print(f"1. Exported test case to: {export_file}")
    
    # Import from file
    imported_case = generator.import_test_case(export_file)
    print(f"2. Imported test case: {imported_case.test_id}")
    print(f"   Components match: {len(test_case.components) == len(imported_case.components)}")
    print(f"   Defects match: {len(test_case.defects) == len(imported_case.defects)}")
    
    # Clean up
    if os.path.exists(export_file):
        os.remove(export_file)
        print(f"3. Cleaned up demo file: {export_file}")


def main():
    """Run the complete demo"""
    print("🚀 mTrac SP Digital Twin Demo")
    print("=" * 40)
    print("This demo showcases the test case generation and digital twin logging capabilities.")
    print()
    
    try:
        # Test case generation demo
        test_cases = demo_test_case_generation()
        
        # Digital twin logging demo
        demo_digital_twin_logging(test_cases)
        
        # Export/import demo
        demo_export_import()
        
        print("\n\n✅ Demo completed successfully!")
        print("=" * 30)
        print("Key features demonstrated:")
        print("• Random test case generation with realistic defects")
        print("• Multiple defect types and severity levels")
        print("• Digital twin logging with comprehensive metrics")
        print("• Performance analytics and session tracking")
        print("• Export/import functionality for test cases")
        print()
        print("To use in the web interface:")
        print("1. Start the backend: python -m backend.server")
        print("2. Open the UI and use the 'Digital Twin Test Cases' section")
        print("3. Generate, load, and run inspection sessions")
        print("4. Review the detailed logs and performance metrics")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r backend/requirements.txt")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
