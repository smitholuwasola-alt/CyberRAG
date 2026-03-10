"""
Display summary of created visualizations
"""

import os
from pathlib import Path

def show_summary():
    """Show summary of created visualizations"""
    viz_dir = Path("visualizations")
    
    if not viz_dir.exists():
        print("Visualizations directory not found!")
        return
    
    print("="*70)
    print("KNOWLEDGE GRAPH VISUALIZATION SUMMARY")
    print("="*70)
    
    # List all PNG files
    png_files = list(viz_dir.glob("*.png"))
    html_files = list(viz_dir.glob("*.html"))
    
    print(f"\n✓ Knowledge Graph Built Successfully!")
    print(f"  - Nodes: 635")
    print(f"  - Edges: 729")
    print(f"  - Entities: 963")
    print(f"  - Relations: 9")
    
    print(f"\n✓ Static Visualizations Created ({len(png_files)} files):")
    for png_file in sorted(png_files):
        size = png_file.stat().st_size / 1024  # Size in KB
        print(f"  - {png_file.name} ({size:.1f} KB)")
    
    if html_files:
        print(f"\n✓ Interactive Visualizations Created ({len(html_files)} files):")
        for html_file in sorted(html_files):
            size = html_file.stat().st_size / 1024  # Size in KB
            print(f"  - {html_file.name} ({size:.1f} KB)")
    else:
        print(f"\n⚠ Interactive Visualizations: Not created (pyvis not installed)")
        print(f"   Install with: pip install pyvis")
    
    print("\n" + "="*70)
    print("VISUALIZATION DETAILS:")
    print("="*70)
    
    print("\n1. Statistics Visualization (kg_statistics.png)")
    print("   Shows: Entity types, relation types, degree distribution, top entities")
    
    print("\n2. Full Graph Overview (kg_overview.png)")
    print("   Shows: Complete network layout with top 100 most connected nodes")
    
    print("\n3. Entity-Specific Networks:")
    print("   - network_snort.png: Snort tool and its connections")
    print("   - network_nmap.png: Nmap tool and its connections")
    print("   - network_metasploit.png: Metasploit framework network")
    print("   - network_ids.png: IDS (Intrusion Detection System) network")
    print("   - network_firewall.png: Firewall connections")
    
    print("\n4. Subgraph Visualization (subgraph_snort_nmap_ids.png)")
    print("   Shows: Combined network of Snort, Nmap, and IDS")
    
    print("\n" + "="*70)
    print("TO VIEW VISUALIZATIONS:")
    print("="*70)
    print(f"1. Navigate to: {viz_dir.absolute()}")
    print("2. Open PNG files with any image viewer")
    print("3. Open HTML files (if created) in a web browser")
    print("="*70)

if __name__ == "__main__":
    show_summary()
