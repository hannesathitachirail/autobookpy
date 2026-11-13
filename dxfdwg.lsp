(defun c:DXFDWG ( / folder files file doc docs fullpath dwgpath)

  (vl-load-com)

  (setq folder "C:\\Users\\T9815037\\Documents\\Hitachi\\WSL\\autobookpy\\out")
  (setq docs (vla-get-Documents (vlax-get-acad-object)))
  (setq files (vl-directory-files folder "*.dxf" 1))

  (foreach file files
    (setq fullpath (strcat folder "\\" file))
    (setq dwgpath (strcat folder "\\" (vl-filename-base file) ".dwg"))

    (princ (strcat "\nConverting: " file))

    (setq doc (vla-open docs fullpath))
    (vla-saveas doc dwgpath)
    (vla-close doc)
  )

  (princ "\nDone.")
  (princ)
)
