#!/usr/bin/env python3
"""
Market Intelligence — Main Entry Point

Run weekly market analysis:
    python main.py --period-days 7

Generate sample report (for testing):
    python main.py --sample
"""

import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from report_generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(
        description='Market Intelligence Report Generator'
    )
    parser.add_argument(
        '--period-days',
        type=int,
        default=7,
        help='Analysis period in days (default: 7 for weekly)'
    )
    parser.add_argument(
        '--sample',
        action='store_true',
        help='Generate sample report with mock data (for testing)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate report but do not publish event'
    )
    
    args = parser.parse_args()
    
    if args.sample:
        print("Sample mode not yet implemented")
        print("Run with --period-days N to analyze real data from discovery events")
        return 1
    
    # Initialize generator
    try:
        generator = ReportGenerator(config_path=args.config)
    except FileNotFoundError:
        print(f"Error: Config file not found: {args.config}")
        return 1
    except Exception as e:
        print(f"Error loading config: {e}")
        return 1
    
    # Generate report
    try:
        report_data = generator.generate_report(period_days=args.period_days)
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Display summary
    print("\n" + "="*60)
    print("MARKET INTELLIGENCE REPORT SUMMARY")
    print("="*60)
    
    data = report_data['data']
    
    print(f"\nPeriod: {report_data['period_start']} to {report_data['period_end']}")
    print(f"Listings analyzed: {data['metadata']['total_listings']}")
    print(f"Unique skills found: {data['metadata']['unique_skills']}")
    
    print("\nTop 10 Skills by Demand:")
    for i, skill in enumerate(data['top_skills'], 1):
        trend_icon = {
            'growing': '↑',
            'declining': '↓',
            'stable': '→',
            'new': '✨',
            'insufficient_data': '?'
        }.get(skill['trend'], '?')
        
        salary = f"${int(skill['avg_salary_usd']/1000)}k" if skill['avg_salary_usd'] else "N/A"
        req_pct = int(skill['required_pct'] * 100)
        
        print(f"  {i:2}. {skill['skill']:20} | {skill['demand_count']:3} mentions | "
              f"{trend_icon} {skill['trend']:15} | {salary:8} avg | {req_pct}% required")
    
    if data.get('salary_ranges'):
        print("\nSalary Ranges by Role:")
        for sr in data['salary_ranges']:
            if sr['median_usd']:
                print(f"  {sr['role_type']:30} | n={sr['sample_size']:3} | "
                      f"median ${int(sr['median_usd']/1000)}k | "
                      f"range ${int(sr['min_usd']/1000)}k-${int(sr['max_usd']/1000)}k")
    
    print("\nGap Analysis:")
    gap = data['gap_analysis']
    print(f"  Strengths: {', '.join(gap['strengths'][:5])}")
    print(f"  Gaps: {', '.join(gap['gaps'][:5])}")
    print(f"  Bridge Skills: {', '.join(gap['bridge_skills'])}")
    
    print("\nKey Insights:")
    for insight in data['insights'][:5]:
        print(f"  • {insight}")
    
    print("\n" + "="*60)
    
    # Publish event
    if not args.dry_run:
        generator.publish_report(report_data)
        print("\n✓ Report published as MarketReportPublished_v1 event")
    else:
        print("\n(Dry run — event not published)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
