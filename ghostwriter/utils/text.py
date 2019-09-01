def deindent_str_block(s, ltrim=False):
    """Remove leading whilespace from lines in block."""
    lines = s.split('\n')
    if ltrim:
        skip_lines = 0
        for line in lines:
            if line.strip() == '':
                skip_lines += 1
            else:
                break
        lines = lines[skip_lines:]
    deindent_by = min((
        len(line) - len(line.lstrip())
        for line in lines
        if len(line.strip()) != 0
    ))
    return '\n'.join([
        line[deindent_by:]
        for line in lines
    ])

