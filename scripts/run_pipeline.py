"""Run the complete pipeline."""

import sys
from database.connection import get_db_context
from pipeline.orchestrator import PipelineOrchestrator

if __name__ == '__main__':
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("Usage: python scripts/run_pipeline.py [limit]")
            sys.exit(1)
    
    print("Running complete pipeline...")
    
    with get_db_context() as db:
        orchestrator = PipelineOrchestrator(db)
        
        results = orchestrator.run_full_pipeline(
            symbols=None,
            limit=limit,
            fetch_data=True,
            calculate_indicators=True,
            analyze_fundamentals=True,
            train_models=True,
            generate_predictions=True,
            generate_reports=True,
            export_json=True,
            display_cli=False
        )
        
        print(f"\nPipeline completed. Processed {len(results)} stocks.")

