' ================================================================
' 建垂直草图平面.bas
'
' 作用：在 3D 草图里，为每条骨架样条的每个"通过点"建一个
'       【垂直于曲线】的草图平面 —— 供画截面轮廓用
'
' 用法：
'   SolidWorks → 工具 → 宏 → 新建（或编辑）→ 粘贴本代码 → 运行
'   或另存为 .swp 后双击运行
'
' 前提：
'   ① 零件已打开
'   ② 3D 草图里有样条（样条上有通过点）
'
' 说明（实测要点，）：
'   · 必须用 SketchManager.CreateSketchPlane，不是 FeatureManager.InsertRefPlane
'     —— 后者对 3D 草图样条一律返回空
'   · 约束常量：PERPENDICULAR=8、COINCIDENT=9、INVALIDCTYPE=0
'   · ★ 选中类型名必须"一致"：
'       草图外 → "EXTSKETCHSEGMENT" + "EXTSKETCHPOINT"
'       草图内 → "SKETCHSEGMENT"    + "SKETCHPOINT"
'     混用（如 EXTSKETCHSEGMENT + SKETCHPOINT）会只选中一个，建面失败
' ================================================================
Option Explicit

Sub main()
    Dim swApp As SldWorks.SldWorks
    Dim swModel As SldWorks.ModelDoc2
    Dim swExt As SldWorks.ModelDocExtension
    Dim swSkMgr As SldWorks.SketchManager
    Dim swSelMgr As SldWorks.SelectionMgr
    Dim swFeat As SldWorks.Feature
    Dim swSketch As SldWorks.Sketch
    Dim vSegs As Variant, swSeg As SldWorks.SketchSegment
    Dim swSpline As SldWorks.SketchSpline
    Dim vPts As Variant, swPt As SldWorks.SketchPoint
    Dim swPlane As Object
    Dim nMade As Long, nFail As Long
    Dim i As Long, j As Long

    Set swApp = Application.SldWorks
    Set swModel = swApp.ActiveDoc
    If swModel Is Nothing Then
        MsgBox "请先打开零件文档"
        Exit Sub
    End If
    Set swExt = swModel.Extension
    Set swSkMgr = swModel.SketchManager
    Set swSelMgr = swModel.SelectionManager

    ' ---- 遍历特征，找 3D 草图 ----
    Set swFeat = swModel.FirstFeature
    Do While Not swFeat Is Nothing
        If swFeat.GetTypeName2 = "3DProfileFeature" Then
            Set swSketch = swFeat.GetSpecificFeature2
            vSegs = swSketch.GetSketchSegments
            If Not IsEmpty(vSegs) Then
                For i = 0 To UBound(vSegs)
                    Set swSeg = vSegs(i)
                    Set swSpline = swSeg          ' 只处理样条
                    vPts = swSpline.GetPoints2
                    If Not IsEmpty(vPts) Then
                        For j = 0 To UBound(vPts)
                            Set swPt = vPts(j)
                            swModel.ClearSelection2 True
                            ' 草图外选择：类型名必须都是 EXT 前缀
                            swExt.SelectByID2 "", "EXTSKETCHSEGMENT", _
                                swPt.X, swPt.Y, swPt.Z, False, 0, Nothing, 0
                            swExt.SelectByID2 "", "EXTSKETCHPOINT", _
                                swPt.X, swPt.Y, swPt.Z, True, 0, Nothing, 0
                            If swSelMgr.GetSelectedObjectCount2(-1) >= 2 Then
                                ' 垂直曲线(8) + 过该点(9)
                                Set swPlane = swSkMgr.CreateSketchPlane(8, 9, 0)
                                If swPlane Is Nothing Then
                                    nFail = nFail + 1
                                Else
                                    nMade = nMade + 1
                                End If
                            Else
                                nFail = nFail + 1
                            End If
                        Next j
                    End If
                Next i
            End If
        End If
        Set swFeat = swFeat.GetNextFeature
    Loop

    swModel.ClearSelection2 True
    swModel.EditRebuild3
    MsgBox "完成：建成 " & nMade & " 个草图平面，失败 " & nFail & " 个"
End Sub
