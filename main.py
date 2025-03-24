import streamlit as st
import re
import pandas as pd

def classify_token(token, lang):
    keywords = {
        "Python": ["False", "None", "True", "and", "as", "assert", "break", "class", "continue", "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"],
        "Java": ["abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class", "const", "continue", "default", "do", "double", "else", "enum", "extends", "final", "finally", "float", "for", "goto", "if", "implements", "import", "instanceof", "int", "interface", "long", "native", "new", "package", "private", "protected", "public", "return", "short", "static", "strictfp", "super", "switch", "synchronized", "this", "throw", "throws", "transient", "try", "void", "volatile", "while"],
        "C++": ["auto", "bool", "break", "case", "char", "class", "const", "continue", "default", "do", "double", "else", "enum", "extern", "false", "float", "for", "goto", "if", "inline", "int", "long", "namespace", "new", "operator", "private", "protected", "public", "return", "short", "signed", "sizeof", "static", "struct", "switch", "template", "this", "throw", "true", "try", "typedef", "typeid", "typename", "union", "unsigned", "using", "virtual", "void", "volatile", "while"]
    }

    operators = {
        "Python": set("+-*/%=!<>|&^~?"),
        "Java": set("+-*/%=!<>|&^~?.:"),
        "C++": set("+-*/%=!<>|&^~?.:"),
    }
    
    delimiters = {
        "Python": set(";,:(){}[]"),
        "Java": set(";,:(){}[]"),
        "C++": set(";,:(){}[]"),
    }
    
    if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
        return "String Literal"
    if token in keywords.get(lang, []):
        return "Keyword"
    elif token.isdigit() or re.match(r'^[0-9]+\.[0-9]+$', token):
        return "Number"
    elif (lang == "Python" and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', token)) or \
         (lang == "Java" and re.match(r'^[a-zA-Z_$][a-zA-Z0-9_$]*$', token)) or \
         (lang == "C++" and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', token)):
        return "Identifier"
    elif any(op in token for op in operators.get(lang, set())):
        return "Operator"
    elif token in delimiters.get(lang, set()):
        return "Delimiter"
    elif lang == "C++" and (token.startswith("#") or token == "<iostream>" or token == "<string>"):
        return "Preprocessor Directive"
    elif lang == "Java" and (token.startswith("@") or token.startswith("import ")):
        return "Import/Annotation"
    else:
        return "Unknown"

def tokenGenerator(code, lang):
    string_literals = []
    def replace_string(match):
        string_literals.append(match.group(0))
        return f"__STRING__{len(string_literals) - 1}__"
    
    comment_patterns = {
        "Python": r'#.*?(?:\n|$)|""".*?"""|\'\'\'.*?\'\'\'',
        "Java": r'//.*?(?:\n|$)|/\*.*?\*/',
        "C++": r'//.*?(?:\n|$)|/\*.*?\*/'
    }

    code_without_comments = re.sub(comment_patterns.get(lang, ''), '', code, flags=re.DOTALL)
    code_with_placeholders = re.sub(r'".*?"|\'.*?\'', replace_string, code_without_comments)
    
    if lang == "Python":
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|\d+\.\d+|\d+|[+\-*/%=!<>|&^~?;,:(){}\[\]]|__STRING__\d+__|\.', code_with_placeholders)
    elif lang == "Java":
        tokens = re.findall(r'[a-zA-Z_$][a-zA-Z0-9_$]*|\d+\.\d+|\d+|[+\-*/%=!<>|&^~?;,:(){}\[\]]|__STRING__\d+__|\.', code_with_placeholders)
    elif lang == "C++":
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|\d+\.\d+|\d+|[+\-*/%=!<>|&^~?;,:(){}\[\]]|__STRING__\d+__|#\w+|<\w+>|\.', code_with_placeholders)
    else:
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|\d+\.\d+|\d+|[+\-*/%=!<>|&^~?;,:(){}\[\]]|__STRING__\d+__|\.', code_with_placeholders)
    
    final_tokens = []
    for token in tokens:
        if token.startswith("__STRING__") and token.endswith("__"):
            index = int(token[10:-2])
            if index < len(string_literals):
                final_tokens.append(string_literals[index])
        else:
            final_tokens.append(token)
    
    if lang == "C++":
        i = 0
        while i < len(final_tokens) - 2:
            if final_tokens[i] == "#" and final_tokens[i+1] == "include" and i+2 < len(final_tokens):
                final_tokens[i] = "#include"
                final_tokens.pop(i+1)
            i += 1
    
    tokenGeneratorTable = []
    for token in final_tokens:
        tokenGeneratorTable.append((token, classify_token(token, lang)))
    
    return tokenGeneratorTable

def get_data_type(value, lang):
    if value.isdigit():
        return "int" if lang in ["Java", "C++"] else "Integer"
    elif re.match(r'^[0-9]+\.[0-9]+$', value):
        return "float" if lang in ["Java", "C++"] else "Float"
    elif (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return "String"
    elif value in ["true", "false"] and lang in ["Java", "C++"]:
        return "boolean" if lang == "Java" else "bool"
    elif value in ["True", "False"] and lang == "Python":
        return "Boolean"
    else:
        return "Unknown"

def symbolTableGenerator(code, lang):
    tokens = tokenGenerator(code, lang)
    symbol_table = []
    identifier_count = 1
    identifier_map = {}
    values_map = {}
    types_map = {} 
    
    if lang == "Python":
        i = 0
        while i < len(tokens):
            token, token_type = tokens[i] 
            if token_type == "Identifier" and i + 2 < len(tokens) and tokens[i+1][1] == "Operator" and "=" in tokens[i+1][0]:
                variable_name = token
                value = tokens[i+2][0]
                data_type = get_data_type(value, lang)
                if data_type != "Unknown":
                    if variable_name not in identifier_map:
                        identifier_map[variable_name] = f"id{identifier_count}"
                        identifier_count += 1
                    values_map[variable_name] = value
                    types_map[variable_name] = data_type
            elif token_type == "Identifier" and token not in identifier_map:
                pass
            i += 1
    
    elif lang == "Java" or lang == "C++":
        i = 0
        while i < len(tokens):
            token, token_type = tokens[i]
            if token_type == "Keyword" and i + 1 < len(tokens) and tokens[i+1][1] == "Identifier":
                data_type = token
                variable_name = tokens[i+1][0]
                if data_type in ["int", "float", "double", "char", "boolean", "bool", "String", "long", "byte", "short"]:
                    if variable_name not in identifier_map:
                        identifier_map[variable_name] = f"id{identifier_count}"
                        identifier_count += 1                 
                    types_map[variable_name] = data_type
                    if i + 3 < len(tokens) and tokens[i+2][0] == "=" and tokens[i+3][1] != "Delimiter":
                        value = tokens[i+3][0]
                        values_map[variable_name] = value
                    else:
                        values_map[variable_name] = "Undefined"
            elif token_type == "Identifier" and token not in identifier_map:
                if (i > 0 and tokens[i-1][0] in ["int", "void", "float", "double", "String"]):
                    identifier_map[token] = f"id{identifier_count}"
                    identifier_count += 1
                    types_map[token] = tokens[i-1][0]
                    values_map[token] = "Undefined"               
            i += 1

    for name, id_number in identifier_map.items():
        if name in types_map and types_map[name] != "Unknown":
            value = values_map.get(name, "Undefined")
            data_type = types_map[name]
            symbol_table.append((id_number, name, data_type, value))
    filtered_identifier_map = {name: id_val for name, id_val in identifier_map.items() 
                               if name in types_map and types_map[name] != "Unknown"}
    return symbol_table, filtered_identifier_map

def replace_identifiers(code, identifier_map):
    pattern = re.compile(r'\b(' + '|'.join(re.escape(key) for key in identifier_map.keys()) + r')\b')
    return pattern.sub(lambda match: identifier_map.get(match.group(0), match.group(0)), code)

def add_missing_header(code, lang):
    if lang == "C++":
        if "#include" not in code:
            return "#include <iostream>\n\n" + code
    elif lang == "Java":
        if "public class" not in code:
            class_name = "Main"
            if not code.strip().startswith("public"):
                return f"public class {class_name} {{\n{code}\n}}"
    return code

st.title("Lexical Analyzer")
language = st.selectbox("Select the Programming Language", ("Python", "Java", "C++"))
code = st.text_area("Enter your code:")

if st.button("Generate Tokens"):
    if code:
        code_with_headers = add_missing_header(code, language) 
        st.write("### Generated Tokens")
        tokenGeneratorTable = tokenGenerator(code_with_headers, language)
        token_count = {}
        for token, token_type in tokenGeneratorTable:
            st.write(f"{token} : {token_type}")
            token_count[token_type] = token_count.get(token_type, 0) + 1
        
        st.write("### Token Summary")
        for token_type, count in token_count.items():
            st.write(f"Number of {token_type}: {count}")

        st.write("### Symbol Table")
        symbolTable, identifier_map = symbolTableGenerator(code_with_headers, language)
        
        if symbolTable:
            df = pd.DataFrame(symbolTable, columns=["ID", "Name", "Type", "Value"])
            st.table(df)
        else:
            st.write("No identifiers with known types found in the code.")
        
        modified_code = replace_identifiers(code_with_headers, identifier_map)
        st.code(modified_code, language=language.lower())

        st.write("This will pass as an input to Syntax Analyzer.")
    else:
        st.error("Please enter some code to analyze.")

st.sidebar.title("About")

st.sidebar.write("""
This tool is a lexical analyzer that generates tokens from a given programming code. It supports Python, Java, and C++ as input languages.

To use this tool, follow these steps:  

1. **Select the Programming Language** : Choose Python, Java, or C++ from the dropdown menu.  
2. **Enter Your Code** : Input your source code into the text area provided.  
3. **Generate Tokens** : Click the "Generate Tokens" button to analyze the code and extract tokens.  
4. **View Token Summary** : The tool will display classified tokens, including keywords, identifiers, operators, and more.  
5. **Check the Symbol Table** : The tool identifies variables and their data types.  
6. **Modified Code Output** : View the updated code with replaced identifiers for further analysis.  
""")
