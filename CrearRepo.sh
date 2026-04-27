echo "# MicroAlgae-CoLaDaS-A-Microalgae-counting-labeling-and-dataset-generation-" >> README.md
date=$(date '+%Y-%m-%d %H:%M:%S')
git init
git add *.*
git commit -m "commit at $date"
git branch -M main
git remote add origin https://github.com/mnunom-upv/MicroAlgae-CoLaDaS-A-Microalgae-counting-labeling-and-dataset-generation-.git
git push -u origin main
