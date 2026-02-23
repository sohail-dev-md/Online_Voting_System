document.addEventListener("DOMContentLoaded", function() {
    var selectedElements = document.querySelectorAll(".option-selected");
    var itemContainers = document.querySelectorAll(".options");

    selectedElements.forEach(function(selected, index) {
        var items = itemContainers[index];

        selected.addEventListener("click", function() {
            items.style.display = items.style.display === "block" ? "none" : "block";
        });

        items.addEventListener("click", function(event) {
            var target = event.target;
            if (target.tagName.toLowerCase() === "div") {
                selected.textContent = target.textContent;
                items.style.display = "none";

                var allItems = items.querySelectorAll("div");
                allItems.forEach(function(item) {
                    item.classList.remove("same-as-selected");
                });

                target.classList.add("same-as-selected");
            }
        });
    });

    document.addEventListener("click", function(event) {
        if (!event.target.closest(".Select")) {
            itemContainers.forEach(function(items) {
                items.style.display = "none";
            });
        }
    });
});
