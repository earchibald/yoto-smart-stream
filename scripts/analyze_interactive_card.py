#!/usr/bin/env python3
"""
Generate a visual flowchart diagram of an interactive Yoto card's branching paths.

Usage:
    python analyze_interactive_card.py /tmp/bar
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
import graphviz


def load_json(filepath):
    """Load and parse the JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def analyze_chapters(data):
    """Analyze the chapter structure and extract branching information."""
    chapters = data.get('chapters', [])
    
    chapter_map = {}
    
    for chapter in chapters:
        key = chapter['key']
        title = chapter['title']
        duration = chapter.get('duration', 0)
        
        chapter_map[key] = {
            'title': title,
            'duration': duration,
            'outgoing': [],
            'is_choice': '[Choice]' in title or '[choice]' in title.lower(),
            'is_ending': '[Ending]' in title or '[ending]' in title.lower(),
        }
        
        # Extract events from first track
        if chapter.get('tracks'):
            track = chapter['tracks'][0]
            events = track.get('events', {})
            
            for event_name, event_data in events.items():
                if event_data.get('cmd') == 'goto':
                    target = event_data['params']['chapterKey']
                    chapter_map[key]['outgoing'].append({
                        'target': target,
                        'trigger': event_name
                    })
    
    return chapter_map


def generate_diagram(json_filepath, output_path):
    """Generate a visual flowchart diagram of the branching narrative."""
    
    # Load and analyze data
    data = json.load(open(json_filepath))
    chapter_map = analyze_chapters(data)
    
    # Create directed graph
    dot = graphviz.Digraph(comment='Interactive Card Branching Paths', format='pdf')
    dot.attr(rankdir='TB', size='11,17!', ratio='fill')
    dot.attr('node', shape='box', style='rounded,filled', fontname='Arial', fontsize='10')
    dot.attr('edge', fontname='Arial', fontsize='9')
    
    # Add nodes for each chapter
    for key, info in chapter_map.items():
        # Determine node color based on type
        if info['is_ending']:
            color = '#e74c3c'  # Red for endings
            shape = 'doubleoctagon'
        elif info['is_choice']:
            color = '#f39c12'  # Orange for choices
            shape = 'diamond'
        else:
            color = '#3498db'  # Blue for regular chapters
            shape = 'box'
        
        # Create label with title and duration
        label = f"{info['title']}\n{info['duration']}s"
        
        dot.node(key, label, fillcolor=color, shape=shape, fontcolor='white' if info['is_ending'] or info['is_choice'] else 'black')
    
    # Add edges for each transition
    for key, info in chapter_map.items():
        for edge in info['outgoing']:
            trigger = edge['trigger']
            target = edge['target']
            
            # Style edges based on trigger type
            if trigger == 'onLhb':
                label = '◄ LEFT'
                color = '#9b59b6'  # Purple
                style = 'bold'
            elif trigger == 'onRhb':
                label = '► RIGHT'
                color = '#16a085'  # Teal
                style = 'bold'
            elif trigger == 'onEnd':
                label = 'AUTO'
                color = '#95a5a6'  # Gray
                style = 'dashed'
            else:
                label = trigger
                color = '#7f8c8d'
                style = 'solid'
            
            dot.edge(key, target, label=label, color=color, style=style, fontcolor=color)
    
    # Render to PDF
    output_file = output_path.replace('.pdf', '')
    dot.render(output_file, cleanup=True)
    print(f"✓ Diagram generated: {output_path}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze_interactive_card.py <json_file> [output.pdf]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'interactive_card_diagram.pdf'
    
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    generate_diagram(input_file, output_file)
    print(f"Diagram complete! View at: {output_file}")
