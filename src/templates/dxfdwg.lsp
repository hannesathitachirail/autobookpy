(defun c:DXFDWG ( / def_dir input_dir folder files file doc docs fullpath dwgpath)

  (vl-load-com)

  ;; Get the directory of the current active drawing
  (setq def_dir (vl-string-right-trim "\\" (getvar "DWGPREFIX")))

  ;; Prompt user for directory, showing the default
  (setq input_dir (getstring T (strcat "\nEnter folder path <" def_dir ">: ")))

  ;; Use default if user presses Enter, otherwise clean up trailing slashes from input
  (if (= input_dir "")
    (setq folder def_dir)
    (setq folder (vl-string-right-trim "\\/" input_dir))
  )

  ;; Verify the folder exists before proceeding
  (if (vl-file-directory-p folder)
    (progn
      (setq docs (vla-get-Documents (vlax-get-acad-object)))
      (setq files (vl-directory-files folder "*.dxf" 1))

      (if files
        (progn
          (foreach file files
            (setq fullpath (strcat folder "\\" file))
            (setq dwgpath (strcat folder "\\" (vl-filename-base file) ".dwg"))

            (princ (strcat "\nConverting: " file))

            (setq doc (vla-open docs fullpath))
            (vla-saveas doc dwgpath)
            (vla-close doc)
          )
          (princ "\nDone.")
        )
        (princ "\nNo DXF files found in the specified directory.")
      )
    )
    (princ (strcat "\nError: Directory does not exist -> " folder))
  )

  (princ)
)

