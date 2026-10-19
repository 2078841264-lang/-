$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$inputDoc = Join-Path $taskRoot '文档\双轴倾转四旋翼数学原理与代码解读.docx'
$renderDir = Join-Path $PSScriptRoot 'render'
New-Item -ItemType Directory -Force -Path $renderDir | Out-Null
$pdfPath = Join-Path $renderDir 'document.pdf'
$wordApp = New-Object -ComObject Word.Application
$wordApp.Visible = $false
$wordApp.DisplayAlerts = 0
$wordDoc = $null
try {
    $wordDoc = $wordApp.Documents.Open($inputDoc, $false, $false)
    $wordDoc.Fields.Update() | Out-Null
    foreach ($tocItem in $wordDoc.TablesOfContents) {
        $tocItem.Update()
        $tocItem.Range.Font.Size = 10.5
        $tocItem.Range.Font.NameFarEast = '宋体'
        $tocItem.Range.ParagraphFormat.SpaceBefore = 0
        $tocItem.Range.ParagraphFormat.SpaceAfter = 3
        $tocItem.Range.ParagraphFormat.LineSpacingRule = 0
        $tocItem.Range.ParagraphFormat.FirstLineIndent = 0
    }
    $wordDoc.Repaginate()
    foreach ($tocItem in $wordDoc.TablesOfContents) { $tocItem.UpdatePageNumbers() }
    $wordDoc.Save()
    $wordDoc.ExportAsFixedFormat($pdfPath, 17)
    'Pages: ' + $wordDoc.ComputeStatistics(2)
    'Equations: ' + $wordDoc.OMaths.Count
    'PDF: ' + $pdfPath
} finally {
    if ($null -ne $wordDoc) { $wordDoc.Close(0); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($wordDoc) }
    $wordApp.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($wordApp)
}
