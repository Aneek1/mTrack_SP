"""
Digital Twin Logger for PCBA Inspection Simulation

This module provides comprehensive logging capabilities for the digital twin,
including defect tracking, inspection metrics, and performance analytics.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from .test_generator import TestCase, DefectInstance, DefectType, DefectSeverity


@dataclass
class InspectionEvent:
    """Represents a single inspection event"""
    timestamp: str
    component_id: str
    inspection_type: str  # "visual", "detailed", "defect_confirmation"
    result: str  # "PASS", "FAIL", "REVIEW"
    confidence: float
    ai_decision: Dict[str, Any]
    gantry_position: Tuple[float, float]
    inspection_duration: float  # seconds
    defect_detected: bool
    defect_details: Optional[Dict[str, Any]] = None


@dataclass
class SessionMetrics:
    """Metrics for an inspection session"""
    session_id: str
    start_time: str
    end_time: Optional[str]
    total_components: int
    inspected_components: int
    passed_components: int
    failed_components: int
    defect_detection_rate: float
    false_positive_rate: float
    average_inspection_time: float
    total_inspection_time: float
    ai_provider: str
    test_case_id: str
    difficulty_level: str
    defects_found: List[Dict[str, Any]]  # Changed from List[Dict[str, Any]] to ensure serializable
    missed_defects: List[Dict[str, Any]]  # Changed from List[Dict[str, Any]] to ensure serializable


@dataclass
class PerformanceMetrics:
    """Performance metrics for the AI inspection system"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    detection_by_defect_type: Dict[str, Dict[str, float]]
    detection_by_severity: Dict[str, Dict[str, float]]
    inspection_efficiency: float  # components per minute
    cost_per_inspection: float  # estimated cost


class DigitalTwinLogger:
    """Comprehensive logging system for digital twin simulation"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.current_session: Optional[str] = None
        self.inspection_events: List[InspectionEvent] = []
        self.current_test_case: Optional[TestCase] = None
        
        # Initialize CSV files
        self._init_csv_files()
    
    def _init_csv_files(self):
        """Initialize CSV log files with headers"""
        # Inspection events log
        self.events_file = self.log_dir / "inspection_events.csv"
        if not self.events_file.exists():
            with open(self.events_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "session_id", "component_id", "inspection_type",
                    "result", "confidence", "ai_decision", "gantry_x", "gantry_y",
                    "inspection_duration", "defect_detected", "defect_type",
                    "defect_severity", "defect_description"
                ])
        
        # Session summary log
        self.sessions_file = self.log_dir / "inspection_sessions.csv"
        if not self.sessions_file.exists():
            with open(self.sessions_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "session_id", "start_time", "end_time", "total_components",
                    "inspected_components", "passed_components", "failed_components",
                    "defect_detection_rate", "false_positive_rate", "avg_inspection_time",
                    "total_inspection_time", "ai_provider", "test_case_id", "difficulty_level"
                ])
        
        # Performance metrics log
        self.metrics_file = self.log_dir / "performance_metrics.csv"
        if not self.metrics_file.exists():
            with open(self.metrics_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "session_id", "timestamp", "accuracy", "precision", "recall",
                    "f1_score", "inspection_efficiency", "cost_per_inspection"
                ])
    
    def start_session(
        self, 
        test_case: TestCase, 
        ai_provider: str,
        session_id: Optional[str] = None
    ) -> str:
        """Start a new inspection session"""
        if session_id is None:
            session_id = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session = session_id
        self.current_test_case = test_case
        self.inspection_events = []
        
        # Log session start
        print(f"Started inspection session: {session_id}")
        print(f"Test Case: {test_case.test_id}")
        print(f"Components: {len(test_case.components)}")
        print(f"Defects: {len(test_case.defects)}")
        print(f"AI Provider: {ai_provider}")
        
        return session_id
    
    def log_inspection_event(
        self,
        component_id: str,
        inspection_type: str,
        result: str,
        confidence: float,
        ai_decision: Dict[str, Any],
        gantry_position: Tuple[float, float],
        inspection_duration: float,
        defect_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an individual inspection event"""
        if not self.current_session:
            raise ValueError("No active session. Call start_session() first.")
        
        defect_detected = result == "FAIL" and defect_details is not None
        
        event = InspectionEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            component_id=component_id,
            inspection_type=inspection_type,
            result=result,
            confidence=confidence,
            ai_decision=ai_decision,
            gantry_position=gantry_position,
            inspection_duration=inspection_duration,
            defect_detected=defect_detected,
            defect_details=defect_details
        )
        
        self.inspection_events.append(event)
        
        # Write to CSV immediately
        self._write_event_to_csv(event)
    
    def _write_event_to_csv(self, event: InspectionEvent):
        """Write inspection event to CSV file"""
        with open(self.events_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                event.timestamp,
                self.current_session,
                event.component_id,
                event.inspection_type,
                event.result,
                event.confidence,
                json.dumps(event.ai_decision),
                event.gantry_position[0],
                event.gantry_position[1],
                event.inspection_duration,
                event.defect_detected,
                event.defect_details.get("defect_type", "") if event.defect_details else "",
                event.defect_details.get("severity", "") if event.defect_details else "",
                event.defect_details.get("description", "") if event.defect_details else ""
            ])
    
    def end_session(self) -> SessionMetrics:
        """End current session and calculate metrics"""
        if not self.current_session or not self.current_test_case:
            raise ValueError("No active session to end.")
        
        end_time = datetime.now(timezone.utc).isoformat()
        
        # Calculate session metrics
        metrics = self._calculate_session_metrics(end_time)
        
        # Write session summary to CSV
        self._write_session_to_csv(metrics)
        
        # Calculate and log performance metrics
        performance = self._calculate_performance_metrics(metrics)
        self._write_performance_to_csv(performance)
        
        # Generate detailed report
        self._generate_session_report(metrics, performance)
        
        print(f"Ended inspection session: {self.current_session}")
        print(f"Inspection rate: {metrics.defect_detection_rate:.1%}")
        print(f"Average time per component: {metrics.average_inspection_time:.2f}s")
        
        self.current_session = None
        self.current_test_case = None
        self.inspection_events = []
        
        return metrics
    
    def _calculate_session_metrics(self, end_time: str) -> SessionMetrics:
        """Calculate comprehensive session metrics"""
        if not self.current_test_case:
            raise ValueError("No test case available")
        
        total_components = len(self.current_test_case.components)
        inspected_components = len(self.inspection_events)
        passed_components = sum(1 for e in self.inspection_events if e.result == "PASS")
        failed_components = sum(1 for e in self.inspection_events if e.result == "FAIL")
        
        # Calculate defect detection metrics
        actual_defects = {d.component_id: d for d in self.current_test_case.defects}
        detected_defects = set()
        false_positives = set()
        
        for event in self.inspection_events:
            if event.defect_detected and event.component_id in actual_defects:
                detected_defects.add(event.component_id)
            elif event.defect_detected and event.component_id not in actual_defects:
                false_positives.add(event.component_id)
        
        defect_detection_rate = len(detected_defects) / len(actual_defects) if actual_defects else 0.0
        false_positive_rate = len(false_positives) / inspected_components if inspected_components > 0 else 0.0
        
        total_inspection_time = sum(e.inspection_duration for e in self.inspection_events)
        average_inspection_time = total_inspection_time / inspected_components if inspected_components > 0 else 0.0
        
        # Identify missed defects
        missed_defects = []
        for defect_id, defect in actual_defects.items():
            if defect_id not in detected_defects:
                missed_defects.append({
                    "component_id": defect.component_id,
                    "defect_type": defect.defect_type.value,
                    "severity": defect.severity.value,
                    "description": defect.description,
                    "confidence": defect.confidence,
                    "location": defect.location,
                    "size": defect.size,
                    "detection_difficulty": defect.detection_difficulty
                })
        
        # Compile found defects
        defects_found = []
        for event in self.inspection_events:
            if event.defect_detected and event.defect_details:
                defects_found.append(event.defect_details)
        
        return SessionMetrics(
            session_id=self.current_session,
            start_time=self.inspection_events[0].timestamp if self.inspection_events else end_time,
            end_time=end_time,
            total_components=total_components,
            inspected_components=inspected_components,
            passed_components=passed_components,
            failed_components=failed_components,
            defect_detection_rate=defect_detection_rate,
            false_positive_rate=false_positive_rate,
            average_inspection_time=average_inspection_time,
            total_inspection_time=total_inspection_time,
            ai_provider="",  # Will be set by the calling code
            test_case_id=self.current_test_case.test_id,
            difficulty_level=self.current_test_case.difficulty_level,
            defects_found=defects_found,
            missed_defects=missed_defects
        )
    
    def _calculate_performance_metrics(self, metrics: SessionMetrics) -> PerformanceMetrics:
        """Calculate detailed performance metrics"""
        # Basic metrics
        accuracy = (metrics.passed_components + len(metrics.defects_found)) / metrics.inspected_components if metrics.inspected_components > 0 else 0.0
        
        # Precision and recall for defect detection
        true_positives = len(metrics.defects_found)
        false_positives = int(metrics.false_positive_rate * metrics.inspected_components)
        false_negatives = len(metrics.missed_defects)
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Detection by defect type and severity
        detection_by_type = self._calculate_detection_by_type(metrics)
        detection_by_severity = self._calculate_detection_by_severity(metrics)
        
        # Efficiency metrics
        inspection_efficiency = 60.0 / metrics.average_inspection_time if metrics.average_inspection_time > 0 else 0.0  # components per minute
        
        # Cost estimation (rough calculation based on AI provider)
        cost_per_inspection = self._estimate_cost_per_inspection(metrics.ai_provider, metrics.total_inspection_time)
        
        return PerformanceMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            detection_by_defect_type=detection_by_type,
            detection_by_severity=detection_by_severity,
            inspection_efficiency=inspection_efficiency,
            cost_per_inspection=cost_per_inspection
        )
    
    def _calculate_detection_by_type(self, metrics: SessionMetrics) -> Dict[str, Dict[str, float]]:
        """Calculate detection rates by defect type"""
        if not self.current_test_case:
            return {}
        
        # Group defects by type
        defects_by_type = {}
        for defect in self.current_test_case.defects:
            defect_type = defect.defect_type.value
            if defect_type not in defects_by_type:
                defects_by_type[defect_type] = {"total": 0, "detected": 0}
            defects_by_type[defect_type]["total"] += 1
        
        # Count detected defects by type
        for defect_found in metrics.defects_found:
            defect_type = defect_found.get("defect_type", "unknown")
            if defect_type in defects_by_type:
                defects_by_type[defect_type]["detected"] += 1
        
        # Calculate detection rates
        detection_rates = {}
        for defect_type, counts in defects_by_type.items():
            detection_rate = counts["detected"] / counts["total"] if counts["total"] > 0 else 0.0
            detection_rates[defect_type] = {
                "detection_rate": detection_rate,
                "total": counts["total"],
                "detected": counts["detected"]
            }
        
        return detection_rates
    
    def _calculate_detection_by_severity(self, metrics: SessionMetrics) -> Dict[str, Dict[str, float]]:
        """Calculate detection rates by defect severity"""
        if not self.current_test_case:
            return {}
        
        # Group defects by severity
        defects_by_severity = {}
        for defect in self.current_test_case.defects:
            severity = defect.severity.value
            if severity not in defects_by_severity:
                defects_by_severity[severity] = {"total": 0, "detected": 0}
            defects_by_severity[severity]["total"] += 1
        
        # Count detected defects by severity
        for defect_found in metrics.defects_found:
            severity = defect_found.get("severity", "unknown")
            if severity in defects_by_severity:
                defects_by_severity[severity]["detected"] += 1
        
        # Calculate detection rates
        detection_rates = {}
        for severity, counts in defects_by_severity.items():
            detection_rate = counts["detected"] / counts["total"] if counts["total"] > 0 else 0.0
            detection_rates[severity] = {
                "detection_rate": detection_rate,
                "total": counts["total"],
                "detected": counts["detected"]
            }
        
        return detection_rates
    
    def _estimate_cost_per_inspection(self, ai_provider: str, total_time: float) -> float:
        """Estimate cost per inspection based on AI provider"""
        # Rough cost estimates (can be refined)
        cost_per_minute = {
            "openai": 0.01,  # ~$0.60 per 1M tokens, rough estimate
            "anthropic": 0.02,  # ~$1.25 per 1M tokens, rough estimate
            "gemini": 0.005,  # ~$0.30 per 1M tokens, rough estimate
        }
        
        cost_per_minute = cost_per_minute.get(ai_provider.lower(), 0.01)
        return cost_per_minute * (total_time / 60.0)
    
    def _write_session_to_csv(self, metrics: SessionMetrics):
        """Write session summary to CSV"""
        with open(self.sessions_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                metrics.session_id,
                metrics.start_time,
                metrics.end_time,
                metrics.total_components,
                metrics.inspected_components,
                metrics.passed_components,
                metrics.failed_components,
                metrics.defect_detection_rate,
                metrics.false_positive_rate,
                metrics.average_inspection_time,
                metrics.total_inspection_time,
                metrics.ai_provider,
                metrics.test_case_id,
                metrics.difficulty_level
            ])
    
    def _write_performance_to_csv(self, performance: PerformanceMetrics):
        """Write performance metrics to CSV"""
        with open(self.metrics_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                self.current_session,
                datetime.now(timezone.utc).isoformat(),
                performance.accuracy,
                performance.precision,
                performance.recall,
                performance.f1_score,
                performance.inspection_efficiency,
                performance.cost_per_inspection
            ])
    
    def _generate_session_report(self, metrics: SessionMetrics, performance: PerformanceMetrics):
        """Generate detailed session report"""
        report_file = self.log_dir / f"session_report_{self.current_session}.json"
        
        # Convert defects to serializable format
        defects_found_serializable = []
        for defect in metrics.defects_found:
            if isinstance(defect, dict):
                defects_found_serializable.append(defect)
            else:
                defects_found_serializable.append(str(defect))
        
        missed_defects_serializable = []
        for defect in metrics.missed_defects:
            if isinstance(defect, dict):
                missed_defects_serializable.append(defect)
            else:
                missed_defects_serializable.append(str(defect))
        
        report_data = {
            "session_info": asdict(metrics),
            "performance_metrics": asdict(performance),
            "defect_analysis": {
                "defects_found": defects_found_serializable,
                "missed_defects": missed_defects_serializable,
                "detection_by_type": performance.detection_by_defect_type,
                "detection_by_severity": performance.detection_by_severity
            },
            "inspection_timeline": [
                {
                    "timestamp": event.timestamp,
                    "component_id": event.component_id,
                    "result": event.result,
                    "duration": event.inspection_duration
                }
                for event in self.inspection_events
            ]
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"Generated detailed report: {report_file}")
    
    def get_session_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent session history"""
        history = []
        try:
            with open(self.sessions_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in list(reader)[-limit:]:
                    history.append(row)
        except FileNotFoundError:
            pass
        
        return history
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary across all sessions"""
        try:
            with open(self.metrics_file, 'r') as f:
                reader = csv.DictReader(f)
                metrics = list(reader)
            
            if not metrics:
                return {}
            
            # Calculate averages
            avg_accuracy = sum(float(m["accuracy"]) for m in metrics) / len(metrics)
            avg_precision = sum(float(m["precision"]) for m in metrics) / len(metrics)
            avg_recall = sum(float(m["recall"]) for m in metrics) / len(metrics)
            avg_f1 = sum(float(m["f1_score"]) for m in metrics) / len(metrics)
            avg_efficiency = sum(float(m["inspection_efficiency"]) for m in metrics) / len(metrics)
            
            return {
                "total_sessions": len(metrics),
                "average_accuracy": avg_accuracy,
                "average_precision": avg_precision,
                "average_recall": avg_recall,
                "average_f1_score": avg_f1,
                "average_efficiency": avg_efficiency,
                "latest_session": metrics[-1]["session_id"] if metrics else None
            }
        
        except FileNotFoundError:
            return {}
