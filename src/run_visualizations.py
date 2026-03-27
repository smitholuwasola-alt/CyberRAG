"""
Quick script to generate all visualizations
"""

import os
import sys
from pathlib import Path

# Get project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent

def main():
    print("="*60)
    print("AISecKG Knowledge Graph Visualization Generator")
    print("="*60)
    
    # Check if knowledge graph exists
    dataset_dir = PROJECT_ROOT / "data" / "knowledge_graph"
    if not dataset_dir.exists():
        print("Error: 'knowledge_graph' directory not found!")
        print(f"Expected at: {dataset_dir}")
        return
    
    # Create visualizations directory
    viz_dir = PROJECT_ROOT / "output" / "visualizations"
    os.makedirs(viz_dir, exist_ok=True)
    
    print("\n1. Generating static visualizations (matplotlib)...")
    try:
        from visualize_kg import main as viz_main
        viz_main()
    except Exception as e:
        print(f"Error creating static visualizations: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n2. Generating interactive visualizations (pyvis)...")
    try:
        from create_interactive_viz import main as interactive_main
        interactive_main()
    except ImportError:
        print("   pyvis not installed. Skipping interactive visualizations.")
        print("   Install with: pip install pyvis")
    except Exception as e:
        print(f"Error creating interactive visualizations: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Visualization generation complete!")
    print("="*60)
    print("\nGenerated files:")
    print("  Static visualizations (PNG):")
    print(f"    - {viz_dir}/kg_statistics.png")
    print(f"    - {viz_dir}/kg_overview.png")
    print(f"    - {viz_dir}/network_*.png")
    print(f"    - {viz_dir}/subgraph_*.png")
    print("\n  Interactive visualizations (HTML):")
    print(f"    - {viz_dir}/kg_interactive_*.html")
    print("\nOpen HTML files in a web browser for interactive exploration!")

if __name__ == "__main__":
    main()
