const fs = require('fs');
const path = require('path');

const srcDir = 'c:\\Users\\VAIBHAVI\\Rescue-connect1\\user_app\\rescue_connect\\authority\\public\\images';
const destDir = 'c:\\Users\\VAIBHAVI\\Rescue-connect1\\Traffic_Model1\\emergency_routing_flutter\\assets\\images';

if (!fs.existsSync(destDir)){
    fs.mkdirSync(destDir, { recursive: true });
}

fs.readdirSync(srcDir).forEach(file => {
    if(file.endsWith('.png')) {
        const srcFile = path.join(srcDir, file);
        const destFile = path.join(destDir, file);
        fs.copyFileSync(srcFile, destFile);
        console.log(`Copied ${file}`);
    }
});
console.log('Copy complete!');
