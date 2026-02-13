
import csv
import re

def clean_line(line):
    line = line.strip()
    cleaned_line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
    return cleaned_line

def process_file():
    with open('raw_competitors.txt', 'r') as f:
        lines = f.readlines()
        
    header = lines[0].strip().split(',')
    
    output_rows = []
    
    for line in lines[1:]:
        if not line.strip(): continue
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line.strip())
        output_rows.append(cleaned)

    with open('competitors.csv', 'w') as f:
        f.write(','.join(header) + '\n')
        for row in output_rows:
            f.write(row + '\n')

process_file()
