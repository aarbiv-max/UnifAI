from mcp.server.fastmcp import FastMCP
import subprocess

# Initialize the MCP server
mcp = FastMCP(
    name="Greeting Server",
    host="0.0.0.0",
    port=8004
)


# --------------------------
# Generic curl tool with cookie
# --------------------------
@mcp.tool()
def curl_request(url: str):
    """
    Executes a curl request to the given URL and returns the response body as a string.
    """

    cookie = "iglooauth=6666ad25-7f75-4194-931b-494ec69864b7"
    try:
        result = subprocess.run(
            ["curl", "-L", "-b", cookie, url],
            capture_output=True,
            text=True,
            timeout=20
        )
        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout
    except Exception as e:
        return f"Exception: {str(e)}"


# --------------------------
# Run the server
# --------------------------
if __name__ == "__main__":
    mcp.run(transport="sse")
