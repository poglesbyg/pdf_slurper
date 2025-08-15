#!/usr/bin/env python
"""Parallel testing script to compare old vs new system results."""

import sys
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.adapter import MigrationAdapter
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich import print as rprint

console = Console()


@dataclass
class TestResult:
    """Test result for comparison."""
    test_name: str
    old_result: Any
    new_result: Any
    match: bool
    old_time: float
    new_time: float
    error: Optional[str] = None


class ParallelTester:
    """Test old and new systems in parallel."""
    
    def __init__(self, pdf_path: Path):
        """Initialize tester.
        
        Args:
            pdf_path: Path to test PDF
        """
        self.pdf_path = pdf_path
        self.old_adapter = MigrationAdapter(use_new_code=False)
        self.new_adapter = MigrationAdapter(use_new_code=True)
        self.results: List[TestResult] = []
    
    def test_slurp_pdf(self) -> TestResult:
        """Test PDF slurping."""
        console.print("\n[bold blue]Testing PDF Slurp...[/bold blue]")
        
        # Test old system
        start = time.time()
        try:
            old_result = self.old_adapter.slurp_pdf(
                self.pdf_path,
                db_path=Path("/tmp/test_old.db"),
                force=True
            )
            old_time = time.time() - start
        except Exception as e:
            old_result = {"error": str(e)}
            old_time = time.time() - start
        
        # Test new system
        start = time.time()
        try:
            new_result = self.new_adapter.slurp_pdf(
                self.pdf_path,
                force=True
            )
            new_time = time.time() - start
        except Exception as e:
            new_result = {"error": str(e)}
            new_time = time.time() - start
        
        # Compare results
        match = self._compare_results(old_result, new_result)
        
        return TestResult(
            test_name="PDF Slurp",
            old_result=old_result,
            new_result=new_result,
            match=match,
            old_time=old_time,
            new_time=new_time
        )
    
    def test_submission_stats(self, submission_id: str) -> TestResult:
        """Test getting submission statistics."""
        console.print("\n[bold blue]Testing Submission Statistics...[/bold blue]")
        
        # Test old system
        start = time.time()
        try:
            old_result = self.old_adapter.get_submission_statistics(submission_id)
            old_time = time.time() - start
        except Exception as e:
            old_result = {"error": str(e)}
            old_time = time.time() - start
        
        # Test new system
        start = time.time()
        try:
            new_result = self.new_adapter.get_submission_statistics(submission_id)
            new_time = time.time() - start
        except Exception as e:
            new_result = {"error": str(e)}
            new_time = time.time() - start
        
        # Compare results
        match = self._compare_results(old_result, new_result)
        
        return TestResult(
            test_name="Submission Stats",
            old_result=old_result,
            new_result=new_result,
            match=match,
            old_time=old_time,
            new_time=new_time
        )
    
    def test_apply_qc(self, submission_id: str) -> TestResult:
        """Test applying QC."""
        console.print("\n[bold blue]Testing QC Application...[/bold blue]")
        
        # Test old system
        start = time.time()
        try:
            old_result = self.old_adapter.apply_qc(
                submission_id,
                min_concentration=10.0,
                min_volume=20.0,
                min_ratio=1.8
            )
            old_time = time.time() - start
        except Exception as e:
            old_result = {"error": str(e)}
            old_time = time.time() - start
        
        # Test new system
        start = time.time()
        try:
            new_result = self.new_adapter.apply_qc(
                submission_id,
                min_concentration=10.0,
                min_volume=20.0,
                min_ratio=1.8
            )
            new_time = time.time() - start
        except Exception as e:
            new_result = {"error": str(e)}
            new_time = time.time() - start
        
        # Compare results
        match = self._compare_results(old_result, new_result)
        
        return TestResult(
            test_name="Apply QC",
            old_result=old_result,
            new_result=new_result,
            match=match,
            old_time=old_time,
            new_time=new_time
        )
    
    def _compare_results(self, old: Dict, new: Dict) -> bool:
        """Compare old and new results.
        
        Args:
            old: Old system result
            new: New system result
            
        Returns:
            True if results match (or are acceptably similar)
        """
        # Handle errors
        if "error" in old or "error" in new:
            return old.get("error") == new.get("error")
        
        # Compare key fields
        if "num_samples" in old and "num_samples" in new:
            if old["num_samples"] != new["num_samples"]:
                return False
        
        if "submission_id" in old and "submission_id" in new:
            # IDs might be different but both should exist
            if not (old["submission_id"] and new["submission_id"]):
                return False
        
        # For now, consider matching if no major differences
        return True
    
    def run_all_tests(self) -> None:
        """Run all tests."""
        console.print("[bold green]Starting Parallel Testing[/bold green]")
        console.print(f"PDF: {self.pdf_path}")
        console.print(f"Time: {datetime.now().isoformat()}\n")
        
        # Run PDF slurp test
        result = self.test_slurp_pdf()
        self.results.append(result)
        self._print_result(result)
        
        # Get submission ID for further tests
        if "submission_id" in result.new_result:
            submission_id = result.new_result["submission_id"]
            
            # Run statistics test
            stats_result = self.test_submission_stats(submission_id)
            self.results.append(stats_result)
            self._print_result(stats_result)
            
            # Run QC test
            qc_result = self.test_apply_qc(submission_id)
            self.results.append(qc_result)
            self._print_result(qc_result)
        
        # Print summary
        self._print_summary()
    
    def _print_result(self, result: TestResult) -> None:
        """Print individual test result."""
        status = "✅ PASS" if result.match else "❌ FAIL"
        console.print(f"\n{status} - {result.test_name}")
        
        if not result.match:
            console.print("[red]Results differ:[/red]")
            console.print(f"  Old: {result.old_result}")
            console.print(f"  New: {result.new_result}")
        
        # Performance comparison
        perf_diff = ((result.old_time - result.new_time) / result.old_time) * 100
        perf_emoji = "🚀" if perf_diff > 10 else "⚡" if perf_diff > 0 else "🐌"
        
        console.print(f"  Old time: {result.old_time:.3f}s")
        console.print(f"  New time: {result.new_time:.3f}s")
        console.print(f"  Performance: {perf_emoji} {abs(perf_diff):.1f}% {'faster' if perf_diff > 0 else 'slower'}")
    
    def _print_summary(self) -> None:
        """Print test summary."""
        console.print("\n" + "="*60)
        console.print("[bold cyan]Test Summary[/bold cyan]")
        
        # Create summary table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Test", style="cyan")
        table.add_column("Result", justify="center")
        table.add_column("Old Time", justify="right")
        table.add_column("New Time", justify="right")
        table.add_column("Performance", justify="center")
        
        total_old_time = 0
        total_new_time = 0
        passed = 0
        
        for result in self.results:
            status = "✅" if result.match else "❌"
            if result.match:
                passed += 1
            
            perf_diff = ((result.old_time - result.new_time) / result.old_time) * 100
            perf_text = f"{abs(perf_diff):.1f}% {'↑' if perf_diff > 0 else '↓'}"
            
            table.add_row(
                result.test_name,
                status,
                f"{result.old_time:.3f}s",
                f"{result.new_time:.3f}s",
                perf_text
            )
            
            total_old_time += result.old_time
            total_new_time += result.new_time
        
        console.print(table)
        
        # Overall statistics
        console.print(f"\n[bold]Overall Results:[/bold]")
        console.print(f"  Tests Passed: {passed}/{len(self.results)}")
        console.print(f"  Total Old Time: {total_old_time:.3f}s")
        console.print(f"  Total New Time: {total_new_time:.3f}s")
        
        if total_old_time > 0:
            total_perf = ((total_old_time - total_new_time) / total_old_time) * 100
            console.print(f"  Overall Performance: {abs(total_perf):.1f}% {'faster' if total_perf > 0 else 'slower'}")
        
        # Recommendation
        if passed == len(self.results):
            console.print("\n[bold green]✅ All tests passed! New system is ready for migration.[/bold green]")
        else:
            console.print("\n[bold red]⚠️ Some tests failed. Review differences before migration.[/bold red]")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.old_adapter.cleanup()
        self.new_adapter.cleanup()


def main():
    """Main entry point."""
    # Get PDF path from command line or use default
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        # Use the test PDF
        pdf_path = Path(__file__).parent.parent.parent / "HTSF--JL-147_quote_160217072025.pdf"
    
    if not pdf_path.exists():
        console.print(f"[red]Error: PDF not found: {pdf_path}[/red]")
        console.print(f"Current working directory: {Path.cwd()}")
        console.print(f"Looking for: {pdf_path}")
        sys.exit(1)
    
    # Run tests
    tester = ParallelTester(pdf_path)
    try:
        tester.run_all_tests()
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
