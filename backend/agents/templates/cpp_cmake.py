"""
C++ / CMake template generator for CrucibAI.

Produces a complete, buildable C++ project with:
- CMakeLists.txt build configuration
- Header / source separation
- Command-line interface in main.cpp
- Core calculator logic
- Basic test file
"""

import re
from typing import Dict


def _extract_domain(goal: str) -> str:
    """Extract a short domain name from the goal."""
    goal_lower = goal.lower()
    for phrase in [
        r"(?:a |an |the )?(\w+)\s+(?:calculator|engine|processor|library|tool)",
        r"(?:build|create|make)\s+(?:a |an |the )?(\w+)",
        r"(\w+)\s+(?:c\+\+|cpp|program)",
    ]:
        match = re.search(phrase, goal_lower)
        if match:
            return match.group(1).replace(" ", "_")
    return "calculator"


def _pascal(word: str) -> str:
    return "".join(part.capitalize() for part in word.split("_"))


def generate_cpp_cmake(goal: str, project_name: str = "generated-cpp") -> Dict[str, str]:
    """Generate a complete C++ / CMake project scaffold.

    Parameters
    ----------
    goal:
        Natural-language description of what the program should do.
    project_name:
        Executable / target name used in CMake.

    Returns
    -------
    Dict[str, str]
        Mapping of relative filepath -> complete file content.
    """
    domain = _extract_domain(goal)
    Domain = _pascal(domain)

    # ------------------------------------------------------------------
    # CMakeLists.txt
    # ------------------------------------------------------------------
    cmake_txt = f'''\
cmake_minimum_required(VERSION 3.16)
project({project_name} VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ---------------------------------------------------------------------------
# Compiler warnings
# ---------------------------------------------------------------------------
if(MSVC)
    add_compile_options(/W4)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ---------------------------------------------------------------------------
# Main executable
# ---------------------------------------------------------------------------
file(GLOB_RECURSE SOURCES CONFIGURE_DEPENDS
    src/*.cpp
)

add_executable({project_name} ${{SOURCES}})
target_include_directories({project_name} PRIVATE ${{CMAKE_SOURCE_DIR}}/include)

# ---------------------------------------------------------------------------
# Tests (optional — requires Catch2 or similar)
# ---------------------------------------------------------------------------
option(BUILD_TESTS "Build unit tests" OFF)
if(BUILD_TESTS)
    enable_testing()
    file(GLOB TEST_SOURCES tests/*.cpp)
    add_executable({project_name}_tests ${{TEST_SOURCES}} src/calculator.cpp)
    target_include_directories({project_name}_tests PRIVATE ${{CMAKE_SOURCE_DIR}}/include)
    add_test(NAME {project_name}_tests COMMAND {project_name}_tests)
endif()
'''

    # ------------------------------------------------------------------
    # include/calculator.h
    # ------------------------------------------------------------------
    calculator_h = f'''\
#ifndef CALCULATOR_H
#define CALCULATOR_H

/**
 * {Domain} — Core computation engine.
 *
 * Provides basic arithmetic operations plus a small expression history
 * so callers can review past computations.
 */

#include <string>
#include <vector>
#include <utility>

struct CalculationResult {{
    double value;
    std::string expression;
    bool success;
    std::string error_message;
}};

class Calculator {{
public:
    Calculator();

    /**
     * Evaluate an arithmetic expression string.
     * Supports +, -, *, / with proper operator precedence.
     * Returns a CalculationResult with the outcome.
     */
    CalculationResult evaluate(const std::string& expression);

    // -- Convenience wrappers -------------------------------------------
    double add(double a, double b);
    double subtract(double a, double b);
    double multiply(double a, double b);
    CalculationResult divide(double a, double b);

    // -- History --------------------------------------------------------
    const std::vector<CalculationResult>& history() const;
    void clear_history();
    int history_size() const;

private:
    std::vector<CalculationResult> history_;

    // Internal recursive descent helpers
    CalculationResult parse_expression(const std::string& expr, size_t& pos);
    CalculationResult parse_term(const std::string& expr, size_t& pos);
    CalculationResult parse_factor(const std::string& expr, size_t& pos);
    void skip_whitespace(const std::string& expr, size_t& pos);
    double parse_number(const std::string& expr, size_t& pos);
}};

#endif // CALCULATOR_H
'''

    # ------------------------------------------------------------------
    # src/calculator.cpp
    # ------------------------------------------------------------------
    calculator_cpp = f'''\
#include "calculator.h"

#include <cctype>
#include <cmath>
#include <stdexcept>
#include <sstream>

// ---------------------------------------------------------------------------
// Constructor
// ---------------------------------------------------------------------------
Calculator::Calculator() {{}}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

CalculationResult Calculator::evaluate(const std::string& expression) {{
    size_t pos = 0;
    try {{
        auto result = parse_expression(expression, pos);
        skip_whitespace(expression, pos);
        if (pos < expression.size()) {{
            return {{0.0, expression, false, "Unexpected characters after expression"}};
        }}
        history_.push_back(result);
        return result;
    }} catch (const std::exception& e) {{
        return {{0.0, expression, false, std::string(e.what())}};
    }}
}}

double Calculator::add(double a, double b) {{
    double result = a + b;
    history_.push_back({{result, std::to_string(a) + " + " + std::to_string(b), true, ""}});
    return result;
}}

double Calculator::subtract(double a, double b) {{
    double result = a - b;
    history_.push_back({{result, std::to_string(a) + " - " + std::to_string(b), true, ""}});
    return result;
}}

double Calculator::multiply(double a, double b) {{
    double result = a * b;
    history_.push_back({{result, std::to_string(a) + " * " + std::to_string(b), true, ""}});
    return result;
}}

CalculationResult Calculator::divide(double a, double b) {{
    if (b == 0.0) {{
        CalculationResult fail = {{0.0, std::to_string(a) + " / " + std::to_string(b), false, "Division by zero"}};
        history_.push_back(fail);
        return fail;
    }}
    double result = a / b;
    CalculationResult ok = {{result, std::to_string(a) + " / " + std::to_string(b), true, ""}};
    history_.push_back(ok);
    return ok;
}}

const std::vector<CalculationResult>& Calculator::history() const {{
    return history_;
}}

void Calculator::clear_history() {{
    history_.clear();
}}

int Calculator::history_size() const {{
    return static_cast<int>(history_.size());
}}

// ---------------------------------------------------------------------------
// Private — recursive descent parser
// ---------------------------------------------------------------------------

void Calculator::skip_whitespace(const std::string& expr, size_t& pos) {{
    while (pos < expr.size() && std::isspace(expr[pos])) {{
        ++pos;
    }}
}}

double Calculator::parse_number(const std::string& expr, size_t& pos) {{
    skip_whitespace(expr, pos);
    size_t start = pos;
    while (pos < expr.size() && (std::isdigit(expr[pos]) || expr[pos] == '.')) {{
        ++pos;
    }}
    if (start == pos) {{
        throw std::runtime_error("Expected a number");
    }}
    return std::stod(expr.substr(start, pos - start));
}}

CalculationResult Calculator::parse_factor(const std::string& expr, size_t& pos) {{
    skip_whitespace(expr, pos);

    // Parenthesised sub-expression
    if (pos < expr.size() && expr[pos] == '(') {{
        ++pos; // skip '('
        auto result = parse_expression(expr, pos);
        skip_whitespace(expr, pos);
        if (pos >= expr.size() || expr[pos] != ')') {{
            throw std::runtime_error("Missing closing parenthesis");
        }}
        ++pos; // skip ')'
        return result;
    }}

    // Unary minus
    if (pos < expr.size() && expr[pos] == '-') {{
        ++pos;
        auto operand = parse_factor(expr, pos);
        operand.value = -operand.value;
        operand.expression = "-" + operand.expression;
        return operand;
    }}

    // Number literal
    size_t num_start = pos;
    double value = parse_number(expr, pos);
    return {{value, expr.substr(num_start, pos - num_start), true, ""}};
}}

CalculationResult Calculator::parse_term(const std::string& expr, size_t& pos) {{
    auto left = parse_factor(expr, pos);

    while (true) {{
        skip_whitespace(expr, pos);
        if (pos >= expr.size()) break;

        char op = expr[pos];
        if (op != '*' && op != '/') break;

        ++pos;
        auto right = parse_factor(expr, pos);

        if (op == '*') {{
            left.value *= right.value;
        }} else {{
            if (right.value == 0.0) {{
                throw std::runtime_error("Division by zero");
            }}
            left.value /= right.value;
        }}
        left.expression = "(" + left.expression + " " + op + " " + right.expression + ")";
    }}

    return left;
}}

CalculationResult Calculator::parse_expression(const std::string& expr, size_t& pos) {{
    auto left = parse_term(expr, pos);

    while (true) {{
        skip_whitespace(expr, pos);
        if (pos >= expr.size()) break;

        char op = expr[pos];
        if (op != '+' && op != '-') break;

        ++pos;
        auto right = parse_term(expr, pos);

        if (op == '+') {{
            left.value += right.value;
        }} else {{
            left.value -= right.value;
        }}
        left.expression = "(" + left.expression + " " + op + " " + right.expression + ")";
    }}

    return left;
}}
'''

    # ------------------------------------------------------------------
    # src/main.cpp
    # ------------------------------------------------------------------
    main_cpp = f'''\
/**
 * {Domain} — command-line calculator application.
 *
 * Auto-generated by CrucibAI.
 *
 * Usage:
 *   ./calculator_app                      — interactive REPL mode
 *   ./calculator_app "2 + 3 * 4"         — evaluate a single expression
 *   ./calculator_app --history            — show computation history
 *   ./calculator_app --clear              — clear history
 */

#include "calculator.h"

#include <iostream>
#include <string>
#include <cstdlib>

void print_help() {{
    std::cout << "{project_name} — A command-line calculator\\n"
              << "\\n"
              << "Usage:\\n"
              << "  " << "{project_name}" << " [EXPRESSION]   Evaluate an expression or enter REPL\\n"
              << "  " << "{project_name}" << " --history       Show computation history\\n"
              << "  " << "{project_name}" << " --clear        Clear history\\n"
              << "  " << "{project_name}" << " --help         Show this help message\\n";
}}

void repl_mode(Calculator& calc) {{
    std::cout << "{Domain} REPL — type an expression or 'quit' to exit.\\n";
    std::string line;
    while (true) {{
        std::cout << "> ";
        std::getline(std::cin, line);
        if (line == "quit" || line == "exit") {{
            break;
        }}
        if (line.empty()) continue;

        auto result = calc.evaluate(line);
        if (result.success) {{
            std::cout << "= " << result.value << "\\n";
        }} else {{
            std::cerr << "Error: " << result.error_message << "\\n";
        }}
    }}
    std::cout << "Goodbye! (" << calc.history_size() << " calculations saved.)\\n";
}}

int main(int argc, char* argv[]) {{
    Calculator calculator;

    // No arguments → REPL mode
    if (argc == 1) {{
        repl_mode(calculator);
        return 0;
    }}

    std::string arg1 = argv[1];

    // Flags
    if (arg1 == "--help" || arg1 == "-h") {{
        print_help();
        return 0;
    }}
    if (arg1 == "--history") {{
        auto hist = calculator.history();
        if (hist.empty()) {{
            std::cout << "No history.\\n";
            return 0;
        }}
        for (size_t i = 0; i < hist.size(); ++i) {{
            const auto& entry = hist[i];
            std::cout << "[" << (i + 1) << "] " << entry.expression;
            if (entry.success) {{
                std::cout << " = " << entry.value;
            }} else {{
                std::cout << " ERROR: " << entry.error_message;
            }}
            std::cout << "\\n";
        }}
        return 0;
    }}
    if (arg1 == "--clear") {{
        calculator.clear_history();
        std::cout << "History cleared.\\n";
        return 0;
    }}

    // Otherwise treat as an expression
    // Rejoin all arguments in case the shell didn't pass a single string
    std::string expression;
    for (int i = 1; i < argc; ++i) {{
        if (i > 1) expression += " ";
        expression += argv[i];
    }}

    auto result = calculator.evaluate(expression);
    if (result.success) {{
        std::cout << result.value << "\\n";
        return 0;
    }} else {{
        std::cerr << "Error: " << result.error_message << "\\n";
        return 1;
    }}
}}
'''

    # ------------------------------------------------------------------
    # tests/test_calculator.cpp
    # ------------------------------------------------------------------
    test_cpp = f'''\
/**
 * Basic unit tests for the Calculator class.
 *
 * Compile with:
 *   g++ -std=c++17 -I../include tests/test_calculator.cpp ../src/calculator.cpp -o test_runner
 * Run:
 *   ./test_runner
 */

#include "calculator.h"

#include <cassert>
#include <cmath>
#include <iostream>
#include <string>

static int tests_passed = 0;
static int tests_failed = 0;

#define TEST(name) \\
    static void name(); \\
    static struct name##_register {{ name##_register() {{ \\
        std::cout << "  [RUN ] " #name << std::endl; \\
        name(); \\
    }} }} name##_instance; \\
    static void name()

#define ASSERT_EQ(a, b) \\
    do {{ \\
        if ((a) != (b)) {{ \\
            std::cerr << "    FAIL: " #a " != " #b << " (" << (a) << " vs " << (b) << ")" << std::endl; \\
            tests_failed++; \\
            return; \\
        }} \\
    }} while (0)

#define ASSERT_TRUE(cond) \\
    do {{ \\
        if (!(cond)) {{ \\
            std::cerr << "    FAIL: " #cond << std::endl; \\
            tests_failed++; \\
            return; \\
        }} \\
    }} while (0)

#define PASS() \\
    do {{ \\
        std::cout << "    PASS" << std::endl; \\
        tests_passed++; \\
    }} while (0)

// =========================================================================
// Tests
// =========================================================================

TEST(test_addition) {{
    Calculator calc;
    double result = calc.add(2.0, 3.0);
    ASSERT_EQ(result, 5.0);
    PASS();
}}

TEST(test_subtraction) {{
    Calculator calc;
    double result = calc.subtract(10.0, 4.0);
    ASSERT_EQ(result, 6.0);
    PASS();
}}

TEST(test_multiplication) {{
    Calculator calc;
    double result = calc.multiply(3.0, 7.0);
    ASSERT_EQ(result, 21.0);
    PASS();
}}

TEST(test_division) {{
    Calculator calc;
    auto result = calc.divide(20.0, 4.0);
    ASSERT_TRUE(result.success);
    ASSERT_EQ(result.value, 5.0);
    PASS();
}}

TEST(test_division_by_zero) {{
    Calculator calc;
    auto result = calc.divide(1.0, 0.0);
    ASSERT_TRUE(!result.success);
    PASS();
}}

TEST(test_evaluate_simple) {{
    Calculator calc;
    auto result = calc.evaluate("2 + 3");
    ASSERT_TRUE(result.success);
    ASSERT_EQ(result.value, 5.0);
    PASS();
}}

TEST(test_evaluate_precedence) {{
    Calculator calc;
    auto result = calc.evaluate("2 + 3 * 4");
    ASSERT_TRUE(result.success);
    ASSERT_EQ(result.value, 14.0);
    PASS();
}}

TEST(test_evaluate_parens) {{
    Calculator calc;
    auto result = calc.evaluate("(2 + 3) * 4");
    ASSERT_TRUE(result.success);
    ASSERT_EQ(result.value, 20.0);
    PASS();
}}

TEST(test_evaluate_nested) {{
    Calculator calc;
    auto result = calc.evaluate("((1 + 2) * (3 + 4)) - 5");
    ASSERT_TRUE(result.success);
    ASSERT_EQ(result.value, 16.0);
    PASS();
}}

TEST(test_history) {{
    Calculator calc;
    calc.evaluate("1 + 1");
    calc.evaluate("2 + 2");
    ASSERT_EQ(calc.history_size(), 2);
    calc.clear_history();
    ASSERT_EQ(calc.history_size(), 0);
    PASS();
}}

// =========================================================================
// Main
// =========================================================================

int main() {{
    std::cout << "Running calculator tests...\\n" << std::endl;

    // Test instances are registered via static constructors above.
    // They have already run by the time main() starts.

    std::cout << "\\nResults: " << tests_passed << " passed, " << tests_failed << " failed." << std::endl;
    return tests_failed == 0 ? 0 : 1;
}}
'''

    return {
        "CMakeLists.txt": cmake_txt,
        "src/main.cpp": main_cpp,
        "src/calculator.cpp": calculator_cpp,
        "include/calculator.h": calculator_h,
        "tests/test_calculator.cpp": test_cpp,
    }
