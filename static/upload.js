const dropArea = document.getElementById('drop-area');
const videoInput = document.getElementById('video-input');
const progressBar = document.querySelector('.progress');
const progressLabel = document.querySelector('.progress-label');
const uploadProgress = document.querySelector('.upload-progress');
const uploadSuccess = document.querySelector('.upload-success');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
  dropArea.addEventListener(eventName, preventDefaults, false)
})

function preventDefaults (e) {
  e.preventDefault()
  e.stopPropagation()
}

['dragenter', 'dragover'].forEach(eventName => {
  dropArea.addEventListener(eventName, highlight, false)
})

['dragleave', 'drop'].forEach(eventName => {
  dropArea.addEventListener(eventName, unhighlight, false)
})

function highlight(e) {
  dropArea.classList.add('highlight')
}

function unhighlight(e) {
  dropArea.classList.remove('highlight')
}

dropArea.addEventListener('drop', handleDrop, false)

function handleDrop(e) {
  let dt = e.dataTransfer
  let files = dt.files

  handleFiles(files)
}

videoInput.addEventListener('change', function() {
    handleFiles(this.files);
});


function handleFiles(files) {
  files = [...files]
  files.forEach(uploadFile)
}

function uploadFile(file) {
  let formData = new FormData()
  formData.append('video', file)

  uploadProgress.style.display = 'block';

  let xhr = new XMLHttpRequest();
  xhr.open('POST', '/upload', true); // Replace with your actual upload URL

  xhr.upload.addEventListener("progress", function(e) {
    let percent = (e.loaded / e.total) * 100;
    progressBar.style.width = percent + '%';
    progressLabel.innerText = `Загрузка ${Math.round(percent)}%`;
  });

  xhr.onload = function() {
    if (xhr.status === 200) {
        uploadProgress.style.display = 'none';
        uploadSuccess.style.display = 'block';

      console.log('Upload successful');
    } else {
      console.error('Upload failed');
    }
  };

  xhr.send(formData);
}
