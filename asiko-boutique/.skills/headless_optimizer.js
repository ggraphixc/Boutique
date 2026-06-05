// .skills/headless_optimizer.js
const fs = require('fs');
const path = require('path');
const { NodeIO } = require('@gltf-transform/core');
const { weld, simplify, textureCompress, prune, dedup } = require('@gltf-transform/functions');

async function optimizeHeadlessMesh(inputPath, outputPath) {
    try {
        console.log(`Initializing structural compression sequence for: ${inputPath}`);
        const io = new NodeIO();
        const document = await io.read(inputPath);

        await document.transform(
            weld(),
            dedup(),
            simplify({
                error: 0.002,
                ratio: 0.25,
                lockBorder: true
            }),
            prune(),
            textureCompress({
                targetFormat: 'webp',
                resize: [1024, 1024]
            })
        );

        await io.write(outputPath, document);
        console.log(`Successfully generated optimized mobile-ready model at: ${outputPath}`);
        process.exit(0);
    } catch (error) {
        console.error(`Asset optimization pipeline execution crash: ${error.message}`);
        process.exit(1);
    }
}

const [,, inputArg, outputArg] = process.argv;
if (!inputArg || !outputArg) {
    console.error("Usage error: node headless_optimizer.js <input.glb> <output.glb>");
    process.exit(1);
}

optimizeHeadlessMesh(path.resolve(inputArg), path.resolve(outputArg));