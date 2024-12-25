document.addEventListener('DOMContentLoaded', function () {
  const uploadCsvForm = document.getElementById('uploadCsvForm');

  uploadCsvForm.addEventListener('submit', function (event) {
    event.preventDefault();

    const formData = new FormData(uploadCsvForm);

    fetch('/upload_csv', {
      method: 'POST',
      body: formData,
    })
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          alert(`Error: ${data.error}`);
        } else {
          alert(data.message);
          location.reload();
        }
      })
      .catch(error => {
        alert('An error occurred. Please try again.');
        console.error(error);
      });
  });
});