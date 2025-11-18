function confirmBorrow(title) {
    return confirm("Are you sure you want to borrow \"" + title + "\"?");
}

window.addEventListener('DOMContentLoaded', () => {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        setTimeout(() => { msg.style.display = 'none'; }, 3000);
    });
});
