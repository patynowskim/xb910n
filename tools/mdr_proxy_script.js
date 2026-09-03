"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const net_1 = __importDefault(require("net"));
const zlib_1 = __importDefault(require("zlib"));
const http_1 = __importDefault(require("http"));
const https_1 = __importDefault(require("https"));
const util_1 = require("util");
const fs_1 = require("fs");
const readline_1 = require("readline");
const crypto_1 = require("crypto");
const hasKey = fs_1.existsSync(`${__dirname}/mdrproxy-key.pem`);
const hasCert = fs_1.existsSync(`${__dirname}/mdrproxy-cert.pem`);
if (!hasKey || !hasCert)
    throw 'Certificate and key (mdrproxy-key and mdrproxy-cert) used by the patched Sony Headphones Connect were not found!';
const FSreadFile = util_1.promisify(fs_1.readFile);
const FSreaddir = util_1.promisify(fs_1.readdir);
const infoXML = `<?xml version="1.0" encoding="UTF-8"?><InformationFile LastUpdate="2019-05-01T00:00:00Z" Noop="false" Version="1.0">
<ControlConditions DefaultServiceStatus="open" DefaultVariance="0"/>
<ApplyConditions>
    <ApplyCondition ApplyOrder="1" Force="false">
        <Rules>
            <Rule Type="System" Key="Model" Value="CUSTOM" Operator="NotEqual"/>
            <Rule Type="System" Key="SerialNo" Value="0" Operator="GreaterThanEqual"/>
            <Rule Type="System" Key="FirmwareVersion" Value="0" Operator="NotEqual"/>
        </Rules>
        <Distributions>
            <Distribution ID="FW" InstallParams="" InstallType="binary" MAC="{FWsha1}" Size="{FWlength}" Type="" URI="https://info.update.sony.net/firmware.bin" Version="1"/>
            <Distribution ID="Disclaimer" InstallParams="" InstallType="notice" MAC="{Disclaimersha1}" Size="{Disclaimerlength}" Type="" URI="https://info.update.sony.net/disclaimer.xml" Version="1"/>
        </Distributions>
        <Descriptions DefaultLang="English">
            <Description Lang="English" Title="CS"><![CDATA[Do not plug in audio cables or USB cables.
              Otherwise, this device may malfunction.]]></Description>
        </Descriptions>
    </ApplyCondition>
</ApplyConditions>
</InformationFile>`;

const disclaimerXML = Buffer.from(`<?xml version="1.0" encoding="UTF-8"?> 

<NoticeFile Version="1.0" DefaultLocale="en-US">
<Notice Locale="en">
<Text><![CDATA[
Update from MDR Proxy

* Please update under the most stable Bluetooth connection environment.
* Please note that you should not update when riding in trains or other vehicles, or in environments where Wi-Fi, microwave ovens, cordless phones, and many other radio waves are mixed with 2.4GHz band radio waves.

[Disclaimer]
0) I shall not be responsible for any loss caused by using this software, you're doing this at your own risk!
1) I strongly recommend to use firmware files for your device. Do not try to flash firmware files meant for other devices!
2) The software update takes about 34 minutes (Android) and 44 minutes (iOS)
Do not "turn off the power" and do not place earbuds in their case during update download, data transfer and update.
Otherwise, the device may become unusable.
2) Please update after confirming that these headphones and Android devices (or iOS devices) have sufficient battery life.
3) If a Bluetooth Low Energy device (wearable terminal, smart watch, etc.) is connected to an Android device (or iOS device), it may not be able to update.
Before updating, please disconnect all Bluetooth devices and Android devices (or iOS devices).
]]></Text>
</Notice>
</NoticeFile>`);


start();
async function start() {
    const select0 = await choose0();
    switch (select0) {
        case '1':
            startProxy('1');
            break;
        case '2':
            const select02 = await choose02();
            switch (select02) {
                case '1':
                    startProxy('21');
                    break;
                case '2':
                    startProxy('22');
                    break;
                case '3':
                    startProxy('23');
                    break;
				case '4':
					startProxy('24');
                    break;
            }
            break;
        case '3':
            const select03 = await choose03();
            startProxy('3', select03);
            break;
        case '4':
            const select04 = await choose03();
            startProxy('4', select04);
            break;
    }
}
function choose() {
    return new Promise(resolve => {
        const rl = readline_1.createInterface({
            input: process.stdin,
            output: process.stdout
        });
        rl.prompt();
        rl.once('line', line => {
            rl.close();
            resolve(line);
        });
    });
}
async function choose0() {
	console.log(``);
	console.log(``);
	console.log(``);
	console.log(``);
    console.log(`   MDR PROXY - FW SIDEGRADE TOOL`);
	console.log(`   Use the provided Sound Connect app APK.`);
	console.log(``);
	console.log(``);
    console.log(`      Choose an option:
   1. Reinstall the firmware (applies the latest available update)
   2. Install a firmware for a different region (applies the latest available update)
   3. Install a certain firwmare - Place the firmware file in the "firmware" folder,
      and then you'll be able to select it in the next screen. Make sure you put a
      correct firmware file for your device! Use with caution!
   4. Install a custom Voice Guidance Pack (VGIDLPB*) - Keeps MDRID* up-to-date
      and patches the requested VGIDLPB* info.xml to serve the selected VP_*.bin.

`);
    const select = await choose();
    if (['1', '2', '3', '4'].includes(select))
        return select;
    else
        return choose0();
}
async function choose02() {
	console.clear();
	console.log(``);
	console.log(``);
	console.log(``);
	console.log(``);
    console.log(`   MDR PROXY - FW SIDEGRADE TOOL`);
	console.log(`   Use the provided Sound Connect app APK.`);
	console.log(``);
	console.log(``);
	console.log(`   Some devices are using the same firmware file for all regions, so using this option
   should do nothing other than reinstalling the latest available firmware update.
   
   Please refer to the list of available regions for each device, as well as if a device is using the same
   firmware file for all regions, which can be found on www.mrwalkman.com.
   
   Close this window and start this app again to choose another option.
	
      Choose the region:
   1. International
   2. Japanese (not available for all devices)
   3. Chinese (not available for all devices)
   4. Japanese (not available for all devices)`);
    const select = await choose();
    if (['1', '2', '3', '4'].includes(select))
        return select;
    else
        return choose02();
}
async function choose03() {
    const files = (await FSreaddir(`${__dirname}/firmware/`)).sort();
	console.clear();
	console.log(``);
	console.log(``);
	console.log(``);
	console.log(``);
    console.log('   MDR PROXY - FW SIDEGRADE TOOL');
	console.log(`   Use the provided Sound Connect app APK.`);
	console.log(``);
	console.log(`
   If you're gonna install an older firmware, a device reset would be recommended afterwards.
   Please refer to the manual of your device for the reset procedure.
   
   When the Sound Connect app will download the firmware, you may see negative percentages.
   This is expected, so no worries about it. The app will download the firmware and then
   it will transfer it to your headphones/buds.
   
   While updating, it is recommended to disable the "Auto turn off" function of your headphones/buds.
   
   Do not close the window while the update is in progress!
   `);
    console.log(`      Choose the FW file (press ENTER to refresh the list):`);
    files.forEach((name, id) => console.log(`   ${id + 1}. ${name}`));
    const select = await choose();
    const file = files[+select - 1];
    if (file !== undefined)
        return await FSreadFile(`${__dirname}/firmware/${file}`);
    else
        return choose03();
}
async function startProxy(mode, fw) {
    const ssl = {
        key: await FSreadFile(`${__dirname}/mdrproxy-key.pem`),
        cert: await FSreadFile(`${__dirname}/mdrproxy-cert.pem`)
    };
    const fakeServer = https_1.default.createServer(ssl)
        .on('request', async (cReq, cRes) => {
        const u = new URL(`https://info.update.sony.net${cReq.url}`);
        console.log('   SONY request:', cReq.method, cReq.url);
        if (u.pathname.endsWith('info.xml')) {
			console.log('   - The Sound Connect app is checking for available updates...');
            const pathSplit = u.pathname.match(/\/(?<categoryID>\w{5})\/(?<serviceID>\w{11})\//);
            if (pathSplit === null)
                nothing();
            else {
                const { categoryID, serviceID } = pathSplit.groups;
                if (mode === '1' || mode[0] === '2') {
                    const newServiceID = mode === '1' ? serviceID : `${serviceID.slice(0, -1)}${Number.parseInt(mode[1]) - 1}`;
                    const XML = await decryptedXML(categoryID, newServiceID);
                    if (XML === undefined)
                        nothing();
                    else {
                        const editedXML = XML.replace(/<Rule Type="System" Key="FirmwareVersion" Value="[\d\.]+" Operator=".+?"\/>/g, '<Rule Type="System" Key="FirmwareVersion" Value="0" Operator="NotEqual"/>');
                        const myXML = await encryptedXML(categoryID, serviceID, editedXML);
                        end(zlib_1.default.gzipSync(myXML), { 'Content-Type': 'application/xml' });
                    }
                }
                else if (mode === '3') {
                    const editedXML = infoXML
                        .replace('{FWsha1}', getHash('sha1', fw))
                        .replace('{FWlength}', fw.length.toString())
                        .replace('{Disclaimersha1}', getHash('sha1', disclaimerXML))
                        .replace('{Disclaimerlength}', disclaimerXML.length.toString());
                    const myXML = await encryptedXML(categoryID, serviceID, editedXML);
                    end(zlib_1.default.gzipSync(myXML), { 'Content-Type': 'application/xml' });
                }
                else if (mode === '4') {
                    const XML = await decryptedXML(categoryID, serviceID);
                    if (XML === undefined)
                        nothing();
                    else if (serviceID.startsWith('MDRID')) {
                        const editedXML = XML.replace(/<Rule Type="System" Key="FirmwareVersion" Value="[\d\.]+" Operator="LessThan"\/>/g, '<Rule Type="System" Key="FirmwareVersion" Value="0.0.0" Operator="LessThan"/>');
                        const myXML = await encryptedXML(categoryID, serviceID, editedXML);
                        end(zlib_1.default.gzipSync(myXML), { 'Content-Type': 'application/xml' });
                    }
                    else if (serviceID.startsWith('VGIDLPB')) {
                        const editedXML = XML.replace(/(<Distribution\b[^>]*\bID="FW"[^>]*>)/, (tag) => tag
                            .replace(/\bMAC="[^"]*"/, `MAC="${getHash('sha1', fw)}"`)
                            .replace(/\bSize="[^"]*"/, `Size="${fw.length}"`));
                        const myXML = await encryptedXML(categoryID, serviceID, editedXML);
                        end(zlib_1.default.gzipSync(myXML), { 'Content-Type': 'application/xml' });
                    }
                    else {
                        nothing();
                    }
                }
                else
                    nothing();
            }
		}
        else if (u.pathname === '/firmware.bin' || (mode === '4' && u.pathname.endsWith('.bin'))) {
			console.log('   - The Sound Connect app is downloading the firmware/voice file of your choosing:', u.pathname);
            end(zlib_1.default.gzipSync(fw), { 'Content-Type': 'application/octet-stream' });
        }
        else if (u.pathname === '/disclaimer.xml') {
			console.log('   - The Sound Connect app is downloading the disclaimer info...');
            end(zlib_1.default.gzipSync(disclaimerXML), { 'Content-Type': 'application/xml' });
        }
        else
            nothing();
        function end(data, headers) {
            cRes.writeHead(200, Object.assign({
                'Accept-Ranges': 'bytes',
                'Content-Encoding': 'gzip',
                'Content-Length': data.length,
            }, headers));
            cRes.on('close', () => console.log(`   - response for ${cReq.url} closed, sent ${cRes.socket ? cRes.socket.bytesWritten : '?'} bytes (body ${data.length}), finished=${cRes.writableFinished}`));
            cRes.write(data, 'binary');
            cRes.end();
        }
        function nothing() {
            const options = {
                hostname: u.hostname,
                port: u.port || 443,
                path: u.pathname,
                method: cReq.method,
                headers: cReq.headers
            };
            const pReq = https_1.default.request(options, pRes => {
                cRes.writeHead(pRes.statusCode, pRes.headers);
                pRes.pipe(cRes);
            }).on('error', () => cRes.end());
            cRes.on('error', () => cReq.destroy());
            cReq.pipe(pReq);
        }
    })
        .listen(0, 'localhost');
    http_1.default.createServer()
        .on('connect', (cReq, cSock, head) => {
        const u = new URL('http://' + cReq.url);
        let port;
        let hostname;
        if (u.hostname === 'info.update.sony.net') {
            port = fakeServer.address().port;
            hostname = 'localhost';
        }
        else {
            port = Number.parseInt(u.port);
            hostname = u.hostname;
        }
        const pSock = net_1.default.connect(port, hostname, () => {
            cSock.write('HTTP/1.1 200 Connection Established\r\n\r\n');
            pSock.write(head);
            pSock.pipe(cSock);
            cSock.pipe(pSock);
        }).on('error', () => cSock.end());
        cSock.on('error', () => pSock.end());
    })
        .listen(8848, '0.0.0.0', () => { 
		console.clear();
		console.log(``);
		console.log(``);
		console.log(``);
		console.log(``);
		console.log(`   MDR PROXY - FW SIDEGRADE TOOL`);
		console.log(`   Use the provided Sound Connect app APK.`);
		console.log(``);
		console.log(`   Process started...`);
		console.log('   Close this window and start this app again to choose another option.');
		console.log(``);
		console.log(``);
		console.log(`   STEP #1) Make sure your smartphone is connected to the same network as the device on which`);
		console.log(`            you're running this software on.`);
		console.log(`   STEP #2) Go to your smartphone's proxy settings and set the following:`);
		console.log(``);
		console.log(`      IP: the local IP of your computer (you could use the "ipconfig" command in CMD to check it)`);
		console.log(`      PORT: 8848`);
		console.log(``);
		console.log(`   Windows Firewall may block communication between MDR Proxy and the Sound Connect app!`);
		console.log(`   If you know what you're doing, add an exception for the 'node' executable, in the Windows Firewall settings.`);
		console.log('   ______________________________________________________________________________________________');
		console.log(``);
		console.log(`   Listening for Sound Connect app requests - connect the headphones/buds, and open the Sound Connect app`); });
		console.log(``);
}
function decryptedXML(categoryID, serviceID) {
    return new Promise(resolve => {
        https_1.default.get(`https://info.update.sony.net/${categoryID}/${serviceID}/info/info.xml`, {
            headers: {
                'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 11; XQ-AT52 Build/58.1.A.5.159)',
                'Accept-Encoding': 'gzip'
            }
        }, res => {
            let cRes;
            let rawData = [];
            switch (res.headers['content-encoding']) {
                case 'gzip':
                    cRes = res.pipe(zlib_1.default.createGunzip());
                    break;
                case 'deflate':
                    cRes = res.pipe(zlib_1.default.createInflate());
                    break;
                default:
                    cRes = res;
                    break;
            }
            cRes
                .on('data', (chunk) => rawData.push(chunk))
                .on('end', () => {
                const data = Buffer.concat(rawData);
                if (res.statusCode !== 200) {
					if (res.statusCode == 404) {
						console.log('');
						console.error('   There is no firmware available for the chosen region.');
						console.log('');
						console.log('   Close this window and start this app again to choose another option.');
						console.log('   ____________________________________________________________________');
						console.log('');
						resolve(undefined);
					}
					else {
						console.log('');
						console.error('   Error:', res.statusCode, data.toString());
						console.log('');
						console.log('   Reopen the Sound Connect app to try again now, or try again later.');
						console.log('   _______________________________________________________________');
						console.log('');
						resolve(undefined);
					}
                }
                else {
                    const headerLength = data.indexOf('\n\n');
                    const header = data.slice(0, headerLength).toString();
                    const headerSplit = header.match(/eaid:(?<eaid>.*)\ndaid:(?<daid>.*)\ndigest:(?<digest>.*)/);
                    if (headerSplit === null) {
                        console.log(header);
                        return resolve(undefined);
                    }
                    const { eaid, daid, digest } = headerSplit.groups;
                    let enc = '';
                    switch (eaid) {
                        case 'ENC0001':
                            enc = 'none';
                            break;
                        case 'ENC0002':
                            enc = 'des-ede3';
                            break;
                        case 'ENC0003':
                            enc = 'aes-128-ecb';
                            break;
                        default:
                            break;
                    }
                    let has = '';
                    switch (daid) {
                        case 'HAS0001':
                            has = 'none';
                            break;
                        case 'HAS0002':
                            has = 'md5';
                            break;
                        case 'HAS0003':
                            has = 'sha1';
                            break;
                        default:
                            break;
                    }
                    if (enc === '' || has === '') {
                        console.log(header);
                        return resolve(undefined);
                    }
                    const cryptedData = data.slice(headerLength + 2);
                    let keyBuffer;
                    let decryptedData = '';
                    if (enc === 'none')
                        decryptedData = cryptedData.toString();
                    else {
                        if (enc === 'des-ede3')
                            keyBuffer = Buffer.alloc(24);
                        else
                            keyBuffer = Buffer.from([79, -94, 121, -103, -1, -48, -117, 31, -28, -46, 96, -43, 123, 109, 60, 23]);
                        const decipher = crypto_1.createDecipheriv(enc, keyBuffer, '');
                        decipher.setAutoPadding(false);
                        decryptedData = Buffer.concat([decipher.update(cryptedData), decipher.final()]).toString();
                    }
                    if (has !== 'none') {
                        const dataHash = getHash(has, decryptedData);
                        const hash = getHash(has, dataHash + serviceID + categoryID);
                        if (hash !== digest) {
                            console.log(header);
                            return resolve(undefined);
                        }
                    }
                    resolve(decryptedData);
                }
            })
                .on('error', e => {
                console.error('Download error.', e);
                resolve(undefined);
            });
        }).on('error', e => {
            console.error('Request error.', e);
            resolve(undefined);
        });
    });
}
function encryptedXML(categoryID, serviceID, decryptedData) {
    return new Promise(resolve => {
        const decryptedDataBuffer = Buffer.from(decryptedData.trimEnd());
        const padBuffer = Buffer.alloc(32 - decryptedDataBuffer.length % 32, ' ');
        const WTFXMLBuffer = padBuffer.length === 32 ? decryptedDataBuffer : Buffer.concat([decryptedDataBuffer, padBuffer]);
        const dataHash = getHash('sha1', WTFXMLBuffer);
        const hash = getHash('sha1', dataHash + serviceID + categoryID);
        const headerBuffer = Buffer.from(`eaid:ENC0003
daid:HAS0003
digest:${hash}

`);
        const keyBuffer = Buffer.from([79, -94, 121, -103, -1, -48, -117, 31, -28, -46, 96, -43, 123, 109, 60, 23]);
        const encipher = crypto_1.createCipheriv('aes-128-ecb', keyBuffer, '');
        encipher.setAutoPadding(false);
        const bodyBuffer = Buffer.concat([encipher.update(WTFXMLBuffer), encipher.final()]);
        const encryptedData = Buffer.concat([headerBuffer, bodyBuffer]);
        resolve(encryptedData);
    });
}
function getHash(algorithm, data) {
    return crypto_1.createHash(algorithm).update(data).digest('hex');
}
