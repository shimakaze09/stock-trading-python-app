"""Run all tests with summary report."""

import subprocess
import sys

def run_tests():
    """Run all tests and print summary."""
    print("=" * 70)
    print("STOCK ANALYSIS PIPELINE - TEST SUITE")
    print("=" * 70)
    print()
    
    # Test categories
    test_modules = [
        ("Configuration", ["tests/test_config.py"]),
        ("Database", ["tests/test_database.py"]),
        ("Technical Analysis", ["tests/test_technical_analysis.py"]),
        ("ML Models", ["tests/test_ml_models.py"]),
        ("Reporting", ["tests/test_reporting.py"]),
        ("Polygon API Client", ["tests/test_polygon_client.py"]),
    ]
    
    results = []
    
    for category, files in test_modules:
        print(f"\n{'='*70}")
        print(f"Testing: {category}")
        print('='*70)
        
        for test_file in files:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
                capture_output=True,
                text=True
            )
            
            # Extract pass/fail count
            output = result.stdout + result.stderr
            passed = output.count("PASSED")
            failed = output.count("FAILED")
            skipped = output.count("SKIPPED")
            errors = output.count("ERROR")
            
            status = "[PASS]" if failed == 0 and errors == 0 else "[FAIL]"
            
            print(f"\n{status} - {test_file}")
            print(f"  Passed: {passed}, Failed: {failed}, Skipped: {skipped}, Errors: {errors}")
            
            results.append({
                'category': category,
                'file': test_file,
                'status': status,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'errors': errors
            })
            
            if failed > 0 or errors > 0:
                # Show error details
                error_lines = [line for line in output.split('\n') if 'FAILED' in line or 'ERROR' in line or 'AssertionError' in line]
                for line in error_lines[:5]:  # Show first 5 error lines
                    print(f"  {line}")
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    total_passed = sum(r['passed'] for r in results)
    total_failed = sum(r['failed'] for r in results)
    total_skipped = sum(r['skipped'] for r in results)
    total_errors = sum(r['errors'] for r in results)
    total_tests = total_passed + total_failed + total_skipped
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"  [PASS] Passed: {total_passed}")
    print(f"  [FAIL] Failed: {total_failed}")
    print(f"  [SKIP] Skipped: {total_skipped}")
    print(f"  [ERROR] Errors: {total_errors}")
    
    if total_failed == 0 and total_errors == 0:
        print("\n[SUCCESS] ALL TESTS PASSED!")
        return 0
    else:
        print("\n[FAILURE] SOME TESTS FAILED")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests())

