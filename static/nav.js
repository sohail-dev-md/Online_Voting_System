document.addEventListener("DOMContentLoaded", function () {
    const navbarCollapse = document.getElementById("navbar");
    const phoneMenuToggler = document.querySelector(".phone-menu-toggler");
    const phoneMenu = document.getElementById("phone-menu");
    const toggleProfileCard = document.getElementById("toggleProfileCard");
    const toggleProfileCardMobile = document.getElementById("toggleProfileCardMobile");
    const profileCard = document.getElementById("profileCard");


    phoneMenuToggler.addEventListener("click", function () {
        if (phoneMenu.style.display === "flex") {
            phoneMenu.style.display = "none";
        } else {
            phoneMenu.style.display = "flex";
        }
    });

    toggleProfileCard.addEventListener("click", function (event) {
        event.preventDefault();
        if (profileCard.style.display === 'none' || profileCard.style.display === '') {
            profileCard.style.display = 'block';
        } else {
            profileCard.style.display = 'none';
        }
    });

    toggleProfileCardMobile.addEventListener("click", function (event) {
        event.preventDefault();
        if (profileCard.style.display === 'none' || profileCard.style.display === '') {
            profileCard.style.display = 'block';
        } else {
            profileCard.style.display = 'none';
        }
    });

    document.getElementById('fileInput').addEventListener('change', function(event) {
        let fileInput = document.getElementById('fileInput');
        let file = fileInput.files[0];

        if (file) {
            // Check if the selected file is an image
            if (!file.type.startsWith('image/')) {
                alert('Please select an image file.');
                return;
            }

            // Update all images locally with class "profil-Picture"
            let reader = new FileReader();
            reader.onload = function(e) {
                let images = document.querySelectorAll('.profil-Picture');
                images.forEach(function(img) {
                    img.src = e.target.result;
                });
            };
            reader.readAsDataURL(file);

            // Prepare and send the file to the server
            let formData = new FormData();
            formData.append('file', file);

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('File uploaded successfully!');
                } else {
                    alert('File upload failed.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('File upload failed.');
            });
        }
    });


    const readonlyFields = document.querySelectorAll('input[readonly]');
    const edit = document.querySelecterAll("editButton");

    edit.addEventListener("change", function(event) {
        readonlyFields.forEach(function(field) {
            field.removeAttribute('readonly');
        });
    })

    console.log("User ID:", userId); // You can now use the userId variable in your JavaScript code
});
