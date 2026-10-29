with open('horizon_clean_theme/snippets/cart-products.liquid', 'r', encoding='utf-8') as f:
    text = f.read()

# Strip all carriage returns
text = text.replace('\r', '')
# Remove duplicate empty lines that were created by \r\r\n
lines = text.split('\n')
clean_lines = []
for i, line in enumerate(lines):
    clean_lines.append(line)

clean_text = '\n'.join(clean_lines)

# Write back with Unix LF or Windows CRLF cleanly
with open('horizon_clean_theme/snippets/cart-products.liquid', 'w', encoding='utf-8', newline='\n') as f:
    f.write(clean_text)

print(f"Total lines: {len(clean_lines)}")
