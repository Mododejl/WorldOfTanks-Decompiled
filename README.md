# WorldOfTanks-Decompiled
Unpacked and decompiled files of **WorldOfTanks**. Each client has its own branch. In the master-branch is the latest release version of the client. The branches of test clients are not released to master-branch.

### Consist
* Python **pyc**-files since client version **0.9.2**
* Game **xml**-files since version **0.9.12**

### Soft
Using **[PjOrion](https://koreanrandom.com/forum/topic/15280-)**:
* **"Uncompile 6"** decompiler updated by **[R. Bernstein](https://github.com/rocky/python-uncompyle6)** and modified **StranikS_Scan**
* Built-in decompressor of xml-files realized by **[SkepticalFox](https://github.com/ShadowHunterRUS)** and modified **StranikS_Scan**

### Decompilation algorithm (recommendations)
1. Create a folder **"source"** and a subfolder **"res"** in it
2. Copy files **"paths.xml"** and **"version.xml"** from game-root to a folder **"source"**
3. Copy all **xml**-files from game folder **"res"** to the directory **"source\res"**
4. Extract the contents of the archive **"res\packages\scripts.pkg"** to the directory **"source\res"**
5. Decode all **xml**-files using **[PjOrion](https://koreanrandom.com/forum/topic/15280-)**: **"WOT-Client"** -> **"Unpack XML"** -> **"Unpack folder..."** select **"source"**
6. Decompile all **pyc**-files using **"Uncompile6"** in PjOrion: **"Decompile"** -> **"Decompile pyc-folder..."** select **"source"**
7. Find and delete all **pyc**-files

### Pull requesting to the repository (recommendations)
1. You need to clone the master-branch if you adding a new client or branch with the exist client otherwise
2. If you adding a new client, then create a new branch with the name as client main version: **"X.X.X"** for release and **"X.X.X_CT"** or **"X.X.X_ST"** for the test clients (Description **"WOT X.X.X #YYY"**)
3. Clean the existing **"source"** directory and put new files there using the algorithm above
4. Change the name of the archive to the current one in the file **"Zip-Packer.arg"**
5. Create an **zip**-archive by running the console program **ZipPacker.cmd** (required **7z.exe**)
6. Clean the existing **"zip"** directory and move to it the new archive
7. Create a commit and offer a **"Pull request"** in the right branch (named as **"X.X.X: ... #YYY"**)

**Note:** Requests with the test clients to the master-branch will be rejected! Main branch only for releases.