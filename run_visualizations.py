"""
Quick script to generate all visualizations
"""

import os
import sys

def main():
    print("="*60)
    print("AISecKG Knowledge Graph Visualization Generator")
    print("="*60)
    
    # Check if dataset exists
    if not os.path.exists("dataset"):
        print("Error: 'dataset' directory not found!")
        print("Please run this script from the AISecKG-cybersecurity-dataset-main directory")
        return
    
    # Create visualizations directory
    os.makedirs("visualizations", exist_ok=True)
    
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
    print("    - visualizations/kg_statistics.png")
    print("    - visualizations/kg_overview.png")
    print("    - visualizations/network_*.png")
    print("    - visualizations/subgraph_*.png")
    print("\n  Interactive visualizations (HTML):")
    print("    - visualizations/kg_interactive_*.html")
    print("\nOpen HTML files in a web browser for interactive exploration!")

if __name__ == "__main__":
    main()
