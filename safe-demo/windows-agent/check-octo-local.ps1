# WhiteBird local diagnostics: read-only, no tokens, no profile data.
# Run on the Windows PC where Octo Browser is installed.
$ErrorActionPreference = 'Stop'
$port = 58888
$report = [ordered]@{
    tool = 'whitebird-octo-local-check'
    timestamp_utc = [DateTime]::UtcNow.ToString('o')
    os = 'Windows'
    port = $port
    local_tcp = 'not_checked'
    local_http = 'not_checked'
    error_type = ''
}
try {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $async = $client.BeginConnect('127.0.0.1', $port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(3000)) {
            $report.local_tcp = 'timeout'
        } else {
            $client.EndConnect($async)
            $report.local_tcp = 'connected'
        }
    } finally {
        $client.Close()
    }
} catch {
    $report.local_tcp = 'unavailable'
    $report.error_type = $_.Exception.GetType().Name
}
if ($report.local_tcp -eq 'connected') {
    try {
        # A 404 is acceptable: it still proves the local HTTP server responded.
        $req = [System.Net.HttpWebRequest]::Create('http://127.0.0.1:58888/')
        $req.Method = 'GET'
        $req.Timeout = 3000
        $req.AllowAutoRedirect = $false
        $response = $req.GetResponse()
        try {
            $report.local_http = [int]$response.StatusCode
        } finally { $response.Close() }
    } catch [System.Net.WebException] {
        $ex = $_.Exception
        if ($null -ne $ex.Response) {
            try {
                $report.local_http = [int]([System.Net.HttpWebResponse]$ex.Response).StatusCode
            } finally { $ex.Response.Close() }
        } else {
            $report.local_http = 'no_response'
            $report.error_type = $ex.GetType().Name
        }
    } catch {
        $report.local_http = 'failed'
        $report.error_type = $_.Exception.GetType().Name
    }
}
# Only safe diagnostic fields; never print environment variables, tokens or URLs with secrets.
$report | ConvertTo-Json -Depth 2
