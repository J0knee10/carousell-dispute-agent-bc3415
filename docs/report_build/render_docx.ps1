param([string]$Docx, [string]$Pdf, [switch]$UpdateAndSave)
# Open a .docx in Word; optionally update all fields (the contents page) and save; export a PDF.
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($Docx, $false, (-not $UpdateAndSave))
    if ($UpdateAndSave) {
        foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
        $doc.Fields.Update() | Out-Null
        foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
        $doc.Save()
    }
    $doc.ExportAsFixedFormat($Pdf, 17)
    $doc.Close($false)
} finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
Write-Output "exported $Pdf"
