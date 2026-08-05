#!/usr/bin/env python3
"""Main runner - processes all 50 cases through the multi-agent pipeline.

Usage:
    python runner.py                  # Process all cases
    python runner.py EC_001           # Process a single case
    python runner.py EC_001 EC_010    # Process specific cases
"""
import asyncio
import json
import os
import sys
import time
import logging
from datetime import datetime
from typing import List

from config import (
    DATA_DIR, INPUT_DIR, OUTPUT_DIR, LOGGING_DIR,
    TRACE_FILE, METADATA_FILE, MODEL_NAME, MODEL_PROVIDER,
    MODEL_BASE_URL, MODEL_API_KEY, TEMPERATURE
)
from data_access import DataAccess
from llm_client import LLMClient
from agents.coordinator_agent import CoordinatorAgent


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(LOGGING_DIR, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ),
    ],
)
logger = logging.getLogger("runner")


def get_case_ids(args: List[str]) -> List[str]:
    """Determine which cases to process."""
    if args:
        return args
    # Default: all 50 cases
    return [f"EC_{str(i).zfill(3)}" for i in range(1, 51)]


async def process_case(coordinator: CoordinatorAgent, case_id: str) -> dict:
    """Process a single case."""
    input_path = os.path.join(INPUT_DIR, f"{case_id}.json")
    
    if not os.path.exists(input_path):
        logger.warning(f"Input file not found: {input_path}")
        return None
    
    with open(input_path, "r", encoding="utf-8") as f:
        case_input = json.load(f)
    
    context = {"case_input": case_input}
    result = await coordinator.process(context)
    return result


async def main():
    """Main entry point."""
    args = sys.argv[1:]
    case_ids = get_case_ids(args)
    
    logger.info(f"Processing {len(case_ids)} cases")
    logger.info(f"Model: {MODEL_NAME}")
    
    # Initialize components
    data_access = DataAccess(DATA_DIR)
    data_access.load()
    logger.info("Data loaded successfully")
    
    llm = LLMClient(
        model_name=MODEL_NAME,
        base_url=MODEL_BASE_URL,
        api_key=MODEL_API_KEY,
        temperature=TEMPERATURE,
    )
    
    coordinator = CoordinatorAgent(llm, data_access)
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Process cases
    trace_entries = []
    start_time = time.time()
    
    for case_id in case_ids:
        case_start = time.time()
        logger.info(f"--- Processing {case_id} ---")
        
        try:
            result = await process_case(coordinator, case_id)
            if result:
                output_path = os.path.join(OUTPUT_DIR, f"{case_id}.json")
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                logger.info(f"{case_id} completed in {time.time() - case_start:.2f}s")
            else:
                logger.warning(f"{case_id} returned no result")
        except Exception as e:
            logger.error(f"{case_id} failed: {e}", exc_info=True)
        
        # Record trace
        trace_entries.append({
            "case_id": case_id,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(time.time() - case_start, 2),
            "status": "success" if result else "error",
            "model": MODEL_NAME,
        })
    
    total_time = time.time() - start_time
    logger.info(f"All cases processed in {total_time:.2f}s")
    
    # Write trace.jsonl
    with open(TRACE_FILE, "w", encoding="utf-8") as f:
        for entry in trace_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.info(f"Trace written to {TRACE_FILE}")
    
    # Write metadata.json
    metadata = {
        "model": MODEL_NAME,
        "parameter_size": "12B",
        "framework": "custom-multi-agent",
        "runtime": f"{total_time:.2f}s",
        "provider": MODEL_PROVIDER,
        "num_cases": len(case_ids),
        "timestamp": datetime.now().isoformat(),
    }
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    logger.info(f"Metadata written to {METADATA_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
