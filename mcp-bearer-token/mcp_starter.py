import os
import asyncio
import logging
import re
import base64
import secrets
import string
from typing import Annotated, Any
from pydantic import Field
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("text-utilities-server")

# Get environment variables
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
MY_NUMBER = os.getenv("MY_NUMBER")

if not AUTH_TOKEN or not MY_NUMBER:
    raise ValueError("❌ Please set AUTH_TOKEN and MY_NUMBER in your .env file")

print(f"🔐 Server configured with token: {AUTH_TOKEN[:10]}...")
print(f"📱 Phone number: {MY_NUMBER}")

# =============================================================================
# TOOL REGISTRATION
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="validate",
            description="Validate bearer token and return phone number for authentication",
            inputSchema={
                "type": "object",
                "properties": {
                    "token": {
                        "type": "string",
                        "description": "Bearer token to validate"
                    }
                },
                "required": ["token"]
            }
        ),
        Tool(
            name="count_text",
            description="Count words, characters, sentences, and paragraphs in text",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to analyze"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="convert_case",
            description="Convert text to different cases (upper, lower, title, camel, snake, kebab, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to convert"
                    },
                    "case_type": {
                        "type": "string",
                        "description": "Case type: upper, lower, title, sentence, camel, pascal, snake, kebab, alternating"
                    }
                },
                "required": ["text", "case_type"]
            }
        ),
        Tool(
            name="clean_text",
            description="Clean text by removing extra spaces, fixing line breaks, and standardizing formatting",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to clean"
                    },
                    "mode": {
                        "type": "string",
                        "description": "Cleaning mode: basic, aggressive, or normalize",
                        "default": "basic"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="base64_converter",
            description="Encode text to Base64 or decode Base64 to text",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to encode or Base64 string to decode"
                    },
                    "operation": {
                        "type": "string",
                        "description": "Operation: 'encode' or 'decode'"
                    }
                },
                "required": ["text", "operation"]
            }
        ),
        Tool(
            name="generate_password",
            description="Generate secure passwords with customizable options",
            inputSchema={
                "type": "object",
                "properties": {
                    "length": {
                        "type": "integer",
                        "description": "Password length (8-50)",
                        "default": 16
                    },
                    "include_symbols": {
                        "type": "boolean",
                        "description": "Include symbols (!@#$%)",
                        "default": True
                    },
                    "include_numbers": {
                        "type": "boolean",
                        "description": "Include numbers (0-9)",
                        "default": True
                    },
                    "exclude_ambiguous": {
                        "type": "boolean",
                        "description": "Exclude similar chars (0,O,l,1,I)",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="extract_data",
            description="Extract emails, URLs, or phone numbers from text",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to search through"
                    },
                    "data_type": {
                        "type": "string",
                        "description": "What to extract: 'emails', 'urls', 'phones', or 'all'"
                    }
                },
                "required": ["text", "data_type"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "validate":
        token = arguments.get("token", "")
        logger.info(f"🔍 Validating token: {token[:10]}...")
        if token == AUTH_TOKEN:
            logger.info("✅ Token validated successfully")
            return [TextContent(type="text", text=MY_NUMBER)]
        else:
            logger.error("❌ Invalid token provided")
            return [TextContent(type="text", text="Invalid token")]
    
    elif name == "count_text":
        text = arguments.get("text", "")
        if not text.strip():
            return [TextContent(type="text", text="❌ Text is empty.")]
        
        # Basic counts
        chars_with_spaces = len(text)
        chars_without_spaces = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
        words = len(text.split())
        
        # Count sentences (basic - ends with . ! ?)
        sentences = len(re.findall(r'[.!?]+', text))
        if sentences == 0:
            sentences = 1  # At least one sentence if there's text
        
        # Count paragraphs
        paragraphs = len([p for p in text.split('\n\n') if p.strip()])
        if paragraphs == 0:  # If no double newlines, count single newlines
            paragraphs = len([p for p in text.split('\n') if p.strip()])
        
        # Count lines
        lines = len(text.split('\n'))
        
        # Estimates
        reading_time = max(1, words // 200)  # Average reading speed
        
        result = f"""📊 **TEXT STATISTICS**

📝 **Basic Counts:**
• Characters (with spaces): {chars_with_spaces:,}
• Characters (no spaces): {chars_without_spaces:,}
• Words: {words:,}
• Sentences: {sentences:,}
• Paragraphs: {paragraphs:,}
• Lines: {lines:,}

📈 **Analysis:**
• Average words per sentence: {words/max(sentences, 1):.1f}
• Average characters per word: {chars_without_spaces/max(words, 1):.1f}
• Estimated reading time: {reading_time} minute(s)

✅ **Analysis complete!**"""
        
        return [TextContent(type="text", text=result)]
    
    elif name == "convert_case":
        text = arguments.get("text", "")
        case_type = arguments.get("case_type", "").lower()
        
        if not text.strip():
            return [TextContent(type="text", text="❌ Text is empty.")]
        
        try:
            if case_type == "upper":
                result = text.upper()
            elif case_type == "lower":
                result = text.lower()
            elif case_type == "title":
                result = text.title()
            elif case_type == "sentence":
                result = text.capitalize()
            elif case_type == "camel":
                words = re.sub(r'[^a-zA-Z0-9\s]', '', text).split()
                if words:
                    result = words[0].lower() + ''.join(word.capitalize() for word in words[1:])
                else:
                    result = text
            elif case_type == "pascal":
                words = re.sub(r'[^a-zA-Z0-9\s]', '', text).split()
                result = ''.join(word.capitalize() for word in words)
            elif case_type == "snake":
                result = re.sub(r'[^a-zA-Z0-9]', '_', text.strip().replace(' ', '_')).lower()
                result = re.sub(r'_+', '_', result).strip('_')
            elif case_type == "kebab":
                result = re.sub(r'[^a-zA-Z0-9]', '-', text.strip().replace(' ', '-')).lower()
                result = re.sub(r'-+', '-', result).strip('-')
            elif case_type == "alternating":
                result = ''.join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text))
            else:
                return [TextContent(type="text", text=f"❌ Invalid case type. Available options:\n• upper, lower, title, sentence\n• camel, pascal, snake, kebab\n• alternating")]
            
            output = f"""✅ **{case_type.upper()} CASE CONVERSION**

**Original:** {text[:100]}{'...' if len(text) > 100 else ''}
**Result:** {result}

📋 **Copy the result above!**"""
            
            return [TextContent(type="text", text=output)]
        
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error converting case: {str(e)}")]
    
    elif name == "clean_text":
        text = arguments.get("text", "")
        mode = arguments.get("mode", "basic")
        
        if not text.strip():
            return [TextContent(type="text", text="❌ Text is empty.")]
        
        original_length = len(text)
        
        try:
            if mode == "basic":
                # Remove extra spaces between words
                cleaned = re.sub(r' +', ' ', text)
                # Remove spaces at start and end of lines
                cleaned = '\n'.join(line.strip() for line in cleaned.split('\n'))
                
            elif mode == "aggressive":
                # Remove all extra whitespace
                cleaned = re.sub(r'\s+', ' ', text).strip()
                
            elif mode == "normalize":
                # Fix line breaks and spacing
                cleaned = text.strip()
                # Replace multiple newlines with double newlines
                cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
                # Remove extra spaces
                cleaned = re.sub(r' +', ' ', cleaned)
                # Clean up each line
                cleaned = '\n'.join(line.strip() for line in cleaned.split('\n'))
                
            else:
                return [TextContent(type="text", text="❌ Invalid mode. Use: basic, aggressive, or normalize")]
            
            saved_chars = original_length - len(cleaned)
            
            result = f"""✅ **TEXT CLEANED ({mode.upper()} MODE)**

📊 **Statistics:**
• Original length: {original_length:,} characters
• Cleaned length: {len(cleaned):,} characters
• Saved: {saved_chars:,} characters ({(saved_chars/original_length*100):.1f}%)

**Cleaned text:**
{cleaned}

📋 **Copy the cleaned text above!**"""
            
            return [TextContent(type="text", text=result)]
        
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error cleaning text: {str(e)}")]
    
    elif name == "base64_converter":
        text = arguments.get("text", "")
        operation = arguments.get("operation", "").lower()
        
        try:
            if operation == "encode":
                encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
                result = f"""✅ **BASE64 ENCODED**

**Original:** {text[:100]}{'...' if len(text) > 100 else ''}
**Encoded:** {encoded}

📋 **Copy the encoded text above!**"""
                return [TextContent(type="text", text=result)]
            
            elif operation == "decode":
                decoded = base64.b64decode(text).decode('utf-8')
                result = f"""✅ **BASE64 DECODED**

**Encoded:** {text[:100]}{'...' if len(text) > 100 else ''}
**Decoded:** {decoded}

📋 **Copy the decoded text above!**"""
                return [TextContent(type="text", text=result)]
            
            else:
                return [TextContent(type="text", text="❌ Invalid operation. Use 'encode' or 'decode'")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error with Base64 operation: {str(e)}")]
    
    elif name == "generate_password":
        length = arguments.get("length", 16)
        include_symbols = arguments.get("include_symbols", True)
        include_numbers = arguments.get("include_numbers", True)
        exclude_ambiguous = arguments.get("exclude_ambiguous", False)
        
        if length < 8 or length > 50:
            return [TextContent(type="text", text="❌ Password length must be between 8 and 50 characters")]
        
        # Character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        numbers = string.digits if include_numbers else ""
        symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?" if include_symbols else ""
        
        # Remove ambiguous characters
        if exclude_ambiguous:
            lowercase = lowercase.replace('l', '')
            uppercase = uppercase.replace('O', '').replace('I', '')
            numbers = numbers.replace('0', '').replace('1', '')
        
        # Combine character sets
        all_chars = lowercase + uppercase + numbers + symbols
        
        if not all_chars:
            return [TextContent(type="text", text="❌ No characters available with current settings")]
        
        # Generate password
        password = ''.join(secrets.choice(all_chars) for _ in range(length))
        
        # Analyze password strength
        has_lower = any(c in lowercase for c in password)
        has_upper = any(c in uppercase for c in password)
        has_digit = any(c in numbers for c in password)
        has_symbol = any(c in symbols for c in password)
        
        strength_score = sum([has_lower, has_upper, has_digit, has_symbol])
        strength_levels = ["Very Weak", "Weak", "Fair", "Good", "Strong"]
        strength = strength_levels[min(strength_score, 4)]
        
        result = f"""🔐 **PASSWORD GENERATED**

**Password:** `{password}`

🛡️ **Security Analysis:**
• **Strength:** {strength}
• **Length:** {length} characters
• **Contains:** {', '.join(filter(None, [
    'lowercase' if has_lower else None,
    'uppercase' if has_upper else None, 
    'numbers' if has_digit else None,
    'symbols' if has_symbol else None
]))}

⚠️ **Remember to store this password securely!**"""
        
        return [TextContent(type="text", text=result)]
    
    elif name == "extract_data":
        text = arguments.get("text", "")
        data_type = arguments.get("data_type", "").lower()
        
        if not text.strip():
            return [TextContent(type="text", text="❌ Text is empty.")]
        
        results = {}
        
        try:
            if data_type in ['emails', 'all']:
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = list(set(re.findall(email_pattern, text)))
                results['emails'] = emails
            
            if data_type in ['urls', 'all']:
                url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                urls = list(set(re.findall(url_pattern, text)))
                results['urls'] = urls
            
            if data_type in ['phones', 'all']:
                phone_patterns = [
                    r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
                    r'\+?[0-9]{1,3}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}'
                ]
                phones = []
                for pattern in phone_patterns:
                    matches = re.findall(pattern, text)
                    phones.extend(['-'.join(match) if isinstance(match, tuple) else match for match in matches])
                results['phones'] = list(set(phones))
            
            if not any(results.values()):
                return [TextContent(type="text", text=f"❌ No {data_type} found in the text.")]
            
            output = "🔍 **EXTRACTED DATA**\n"
            total_found = 0
            
            for category, items in results.items():
                if items:
                    emoji = {"emails": "📧", "urls": "🔗", "phones": "📱"}.get(category, "📄")
                    output += f"\n{emoji} **{category.upper()}** ({len(items)} found):\n"
                    for item in items[:10]:  # Limit to 10 items per category
                        output += f"• {item}\n"
                    if len(items) > 10:
                        output += f"• ... and {len(items) - 10} more\n"
                    total_found += len(items)
            
            output += f"\n✅ **Total found:** {total_found} items"
            return [TextContent(type="text", text=output)]
        
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error extracting data: {str(e)}")]
    
    else:
        return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]

# =============================================================================
# SERVER STARTUP
# =============================================================================

async def main():
    """Run the MCP server."""
    print("=" * 50)
    print("🚀 STARTING TEXT UTILITIES MCP SERVER")
    print("=" * 50)
    print(f"🔧 Server: text-utilities-server")
    print(f"🔐 Auth token: {AUTH_TOKEN[:10]}...")
    print(f"📱 Phone: {MY_NUMBER}")
    print(f"🎯 Tools available: 7 text utilities")
    print("=" * 50)
    
    try:
        async with stdio_server() as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise
    