#!/usr/bin/env python3
"""
Generate a Getting Started PDF for Yoto Smart Stream.
This script creates a user-friendly walkthrough with screenshots.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor
import os

def create_pdf():
    # Output PDF path
    pdf_path = "docs/getting-started.pdf"
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#2563eb'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Custom heading style
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=HexColor('#1e40af'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    # Custom body style
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        leading=14
    )
    
    # Title Page
    elements.append(Spacer(1, 2*inch))
    elements.append(Paragraph("Yoto Smart Stream", title_style))
    elements.append(Paragraph("Getting Started Guide", title_style))
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("A Visual Walkthrough for New Users", heading_style))
    elements.append(PageBreak())
    
    # Introduction
    elements.append(Paragraph("Welcome to Yoto Smart Stream", heading_style))
    elements.append(Paragraph(
        "Yoto Smart Stream is a powerful service that lets you stream audio content to your "
        "Yoto players, create custom audio cards, and manage your Yoto library. This guide will "
        "walk you through the main features and show you how to get started.",
        body_style
    ))
    elements.append(Spacer(1, 0.3*inch))
    
    # Table of Contents
    elements.append(Paragraph("What You'll Learn", heading_style))
    elements.append(Paragraph("• Navigating the Dashboard", body_style))
    elements.append(Paragraph("• Managing Connected Players", body_style))
    elements.append(Paragraph("• Creating Smart Streams with Different Play Modes", body_style))
    elements.append(Paragraph("• Browsing Your Yoto Library", body_style))
    elements.append(Paragraph("• Accessing API Documentation", body_style))
    elements.append(PageBreak())
    
    # Section 1: Dashboard
    elements.append(Paragraph("1. The Dashboard", heading_style))
    elements.append(Paragraph(
        "The Dashboard is your central hub for monitoring and controlling your Yoto ecosystem. "
        "Here you can see all your connected Yoto players, their current status, battery levels, "
        "and quickly access your audio files.",
        body_style
    ))
    elements.append(Spacer(1, 0.2*inch))
    
    # Add dashboard screenshot
    screenshot_path = "docs/screenshots/01-dashboard.png"
    if os.path.exists(screenshot_path):
        img = Image(screenshot_path, width=6*inch, height=6*inch*0.75)  # 4:3 aspect ratio
        elements.append(img)
    else:
        elements.append(Paragraph(
            "[Dashboard screenshot would appear here]",
            body_style
        ))
    
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("Key Features:", heading_style))
    elements.append(Paragraph(
        "• <b>System Status:</b> View the number of connected players, available audio files, "
        "MQTT connection status, and current environment.",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Player Controls:</b> Each connected player shows its status (online/offline), "
        "battery level, current volume, and playback controls. You can adjust volume, skip tracks, "
        "or pause directly from the dashboard.",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Audio Library Preview:</b> Browse your available audio files with preview players "
        "to hear content before adding it to streams.",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Quick Actions:</b> Access text-to-speech generation, refresh data, view API docs, "
        "or manage streams with one click.",
        body_style
    ))
    elements.append(PageBreak())
    
    # Section 2: Smart Streams
    elements.append(Paragraph("2. Smart Streams", heading_style))
    elements.append(Paragraph(
        "Smart Streams are the heart of Yoto Smart Stream. They allow you to create custom audio "
        "experiences by combining your audio files with flexible play modes. Whether you want a "
        "sequential story playlist or an endless shuffle of songs, Smart Streams has you covered.",
        body_style
    ))
    elements.append(Spacer(1, 0.2*inch))
    
    # Add smart streams screenshot
    screenshot_path = "docs/screenshots/02-smart-streams.png"
    if os.path.exists(screenshot_path):
        img = Image(screenshot_path, width=6*inch, height=6*inch*0.75)
        elements.append(img)
    else:
        elements.append(Paragraph(
            "[Smart Streams screenshot would appear here]",
            body_style
        ))
    
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("Play Modes:", heading_style))
    elements.append(Paragraph(
        "• <b>Sequential:</b> Plays tracks in order from start to finish, perfect for audiobooks "
        "and story series.",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Loop:</b> Repeats the playlist continuously, great for bedtime stories or "
        "background music.",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Shuffle:</b> Randomizes the order of tracks for variety while keeping all content.",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Endless Shuffle:</b> Randomly plays tracks with the possibility of repetition, "
        "creating an infinite playlist experience.",
        body_style
    ))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(
        "Each stream shows its track count, availability status, and play mode. You can preview "
        "the queue to see what's coming up next, and create new streams using the form at the bottom.",
        body_style
    ))
    elements.append(PageBreak())
    
    # Section 3: Library
    elements.append(Paragraph("3. Your Yoto Library", heading_style))
    elements.append(Paragraph(
        "The Library page displays all your Yoto cards and playlists in one place. This includes "
        "both official Yoto cards you've purchased and custom cards you've created (Make Your Own cards).",
        body_style
    ))
    elements.append(Spacer(1, 0.2*inch))
    
    # Add library screenshot
    screenshot_path = "docs/screenshots/03-library.png"
    if os.path.exists(screenshot_path):
        img = Image(screenshot_path, width=6*inch, height=6*inch*0.75)
        elements.append(img)
    else:
        elements.append(Paragraph(
            "[Library screenshot would appear here]",
            body_style
        ))
    
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("Library Features:", heading_style))
    elements.append(Paragraph(
        "• <b>Browse Your Collection:</b> View all your cards in a visual grid with cover art "
        "and titles.",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Filter Cards:</b> Use the search box to quickly find specific cards by name.",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Refresh Library:</b> Update your library to see newly added cards from your "
        "Yoto account.",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Statistics:</b> See at a glance how many cards and playlists you have in "
        "your collection.",
        body_style
    ))
    elements.append(PageBreak())
    
    # Next Steps
    elements.append(Paragraph("Next Steps", heading_style))
    elements.append(Paragraph(
        "Now that you're familiar with the main features of Yoto Smart Stream, here are some "
        "suggested next steps:",
        body_style
    ))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(
        "• <b>Create Your First Stream:</b> Go to the Smart Streams page and combine some of your "
        "favorite audio files into a custom playlist. Experiment with different play modes!",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Generate a Streaming Card:</b> Once you've created a stream, use the 'Create Card' "
        "feature to generate a QR code that you can scan with your Yoto player.",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Upload Custom Audio:</b> Add your own MP3 files to create truly personalized "
        "content for your Yoto players.",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Try Text-to-Speech:</b> Use the TTS feature to convert text into spoken audio, "
        "perfect for custom stories or messages.",
        body_style
    ))
    elements.append(Paragraph(
        "• <b>Explore the API:</b> If you're technical, check out the API Documentation to "
        "integrate Yoto Smart Stream with your own applications.",
        body_style
    ))
    elements.append(Spacer(1, 0.3*inch))
    
    # Support
    elements.append(Paragraph("Getting Help", heading_style))
    elements.append(Paragraph(
        "If you need assistance or have questions:",
        body_style
    ))
    elements.append(Paragraph(
        "• Visit the GitHub repository for documentation and updates",
        body_style
    ))
    elements.append(Paragraph(
        "• Check the API Documentation (linked from the dashboard) for technical details",
        body_style
    ))
    elements.append(Paragraph(
        "• Refer to the official Yoto API documentation at yoto.dev",
        body_style
    ))
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    elements.append(Spacer(1, 1*inch))
    elements.append(Paragraph(
        "Happy Streaming! 🎵",
        title_style
    ))
    
    # Build PDF
    doc.build(elements)
    print(f"PDF created successfully: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    pdf_path = create_pdf()
    print(f"\n✅ Getting Started PDF generated at: {pdf_path}")
    print("This PDF is for local use only and has not been committed to git.")
