import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, Image, ScrollView,
  TextInput, StyleSheet, Alert, ActivityIndicator, SafeAreaView
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';

// ─── CHANGE THESE TO YOUR PC's LOCAL IP ADDRESS ───────────────
// Find it: Windows → ipconfig  |  Mac/Linux → ifconfig
// Your phone and PC must be on the SAME Wi-Fi network
const PYTHON = 'http://10.144.92.144:5001';
const JAVA   = 'http://10.144.92.144:8080/api';
// ─────────────────────────────────────────────────────────────

export default function App() {
  const [tab, setTab]             = useState('scan');
  const [image, setImage]         = useState(null);
  const [scanning, setScanning]   = useState(false);
  const [results, setResults]     = useState(null);
  const [annotated, setAnnotated] = useState(null);
  const [rfidUid, setRfidUid]     = useState('');
  const [rfidShelf, setRfidShelf] = useState('A1');
  const [rfidResult, setRfidResult] = useState(null);
  const [rfidLoading, setRfidLoading] = useState(false);

  const pickImage = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') { Alert.alert('Permission needed'); return; }
    const r = await ImagePicker.launchImageLibraryAsync({ quality: 0.85 });
    if (!r.canceled) { setImage(r.assets[0]); setResults(null); setAnnotated(null); }
  };

  const takePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') { Alert.alert('Camera permission needed'); return; }
    const r = await ImagePicker.launchCameraAsync({ quality: 0.85 });
    if (!r.canceled) { setImage(r.assets[0]); setResults(null); setAnnotated(null); }
  };

  const scanImage = async () => {
    if (!image) { Alert.alert('Select or take a photo first'); return; }
    setScanning(true);
    try {
      const fd = new FormData();
      fd.append('image', { uri: image.uri, name: 'shelf.jpg', type: 'image/jpeg' });
      const r = await fetch(PYTHON + '/process-image', {
        method: 'POST', body: fd,
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const d = await r.json();
      setResults(d);
      if (d.annotated_image) setAnnotated('data:image/jpeg;base64,' + d.annotated_image);
    } catch {
      Alert.alert('Error', 'Cannot reach Python server.\nCheck YOUR_PC_IP and make sure app.py is running.');
    } finally { setScanning(false); }
  };

  const checkRfid = async () => {
    if (!rfidUid) { Alert.alert('Enter UID'); return; }
    setRfidLoading(true);
    try {
      const r = await fetch(JAVA + '/rfid/lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uid: rfidUid.toUpperCase(), shelfId: rfidShelf.toUpperCase() }),
      });
      setRfidResult(await r.json());
    } catch {
      Alert.alert('Error', 'Cannot reach Java backend.\nCheck YOUR_PC_IP and make sure Spring Boot is running.');
    } finally { setRfidLoading(false); }
  };

  const SHELVES = [
    {id:'A1',cat:'Mathematics',n:700,cap:800},
    {id:'A2',cat:'Physics',n:136,cap:200},
    {id:'A3',cat:'Chemistry',n:718,cap:800},
    {id:'B1',cat:'Biotechnology',n:749,cap:800},
    {id:'B2',cat:'Computer Engineering',n:813,cap:900},
    {id:'B3',cat:'Mechanical Engineering',n:1639,cap:1700},
    {id:'C1',cat:'Chemical Engineering',n:814,cap:900},
    {id:'C2',cat:'Civil / Fire Safety',n:742,cap:900},
    {id:'C3',cat:'Management',n:1501,cap:1600},
    {id:'D1',cat:'General / Law / Skills',n:484,cap:600},
    {id:'D2',cat:'Start-up / SSIP',n:34,cap:100},
  ];

  return (
    <SafeAreaView style={s.safe}>
      <View style={s.tabs}>
        {[['scan','📸 Camera'],['rfid','📡 RFID'],['shelves','📍 Shelves']].map(([t,lbl]) => (
          <TouchableOpacity key={t} style={[s.tab, tab===t&&s.tabActive]} onPress={()=>setTab(t)}>
            <Text style={[s.tabTxt, tab===t&&s.tabTxtActive]}>{lbl}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView style={s.body} contentContainerStyle={{paddingBottom:40}}>

        {tab==='scan' && (
          <View>
            <Text style={s.h1}>Camera Scan</Text>
            <Text style={s.sub}>YOLO + OCR — shelf auto-detected</Text>
            <View style={s.row}>
              <TouchableOpacity style={[s.btn,s.btnBlue,{flex:1}]} onPress={pickImage}>
                <Text style={s.btnT}>📂 Gallery</Text>
              </TouchableOpacity>
              <View style={{width:10}}/>
              <TouchableOpacity style={[s.btn,s.btnBlue,{flex:1}]} onPress={takePhoto}>
                <Text style={s.btnT}>📷 Camera</Text>
              </TouchableOpacity>
            </View>
            {image && <Image source={{uri:image.uri}} style={s.img} resizeMode="contain"/>}
            <TouchableOpacity style={[s.btn,s.btnGreen,{marginTop:10}]} onPress={scanImage} disabled={scanning}>
              {scanning ? <ActivityIndicator color="#fff"/> : <Text style={s.btnT}>🔍 Detect Books</Text>}
            </TouchableOpacity>

            {results && (
              <View style={s.card}>
                <Text style={s.cardH}>
                  Shelf: {results.detectedShelf} • {results.total_matched}/{(results.books||[]).length} matched
                  {results.used_fallback ? '  ⚠️ OCR Fallback' : ''}
                </Text>
                {annotated && <Image source={{uri:annotated}} style={s.img} resizeMode="contain"/>}
                {(results.books||[]).map((b,i) => (
                  <View key={i} style={[s.brow, b.status==='OK'&&s.bok, b.status==='WRONG'&&s.bwr]}>
                    <Text style={s.btit}>
                      {b.found?(b.status==='OK'?'✅':'❌'):'❓'} {b.title||b.code}
                    </Text>
                    {b.found && (
                      <Text style={s.bsub}>
                        {b.code} • {b.rack} • Expected: {b.expectedShelf}
                        {b.status==='WRONG'?' ← MISPLACED':''}
                      </Text>
                    )}
                  </View>
                ))}
                {(results.books||[]).length===0 && (
                  <Text style={s.bsub}>
                    No books detected.{'\n'}
                    Tips: Good lighting, hold steady, label stickers must be visible.
                  </Text>
                )}
              </View>
            )}
          </View>
        )}

        {tab==='rfid' && (
          <View>
            <Text style={s.h1}>RFID Lookup</Text>
            <Text style={s.sub}>Same unified books database as Camera Scan</Text>
            <Text style={s.lbl}>RFID Tag UID</Text>
            <TextInput style={s.inp} value={rfidUid} onChangeText={t=>setRfidUid(t.toUpperCase())}
              placeholder="e.g. FA7819C1" placeholderTextColor="#555" autoCapitalize="characters"/>
            <Text style={s.lbl}>Current Shelf</Text>
            <TextInput style={s.inp} value={rfidShelf} onChangeText={t=>setRfidShelf(t.toUpperCase())}
              placeholder="e.g. A1" placeholderTextColor="#555" autoCapitalize="characters"/>
            <TouchableOpacity style={[s.btn,s.btnGreen,{marginTop:10}]} onPress={checkRfid} disabled={rfidLoading}>
              {rfidLoading ? <ActivityIndicator color="#fff"/> : <Text style={s.btnT}>🔎 Check Book</Text>}
            </TouchableOpacity>
            {rfidResult && (
              <View style={[s.card, rfidResult.found&&rfidResult.status==='OK'&&s.bok,
                            rfidResult.found&&rfidResult.status==='WRONG'&&s.bwr]}>
                {!rfidResult.found ? (
                  <Text style={s.cardH}>⚠️ UID not found — no RFID sticker assigned yet</Text>
                ) : (
                  <>
                    <Text style={s.cardH}>{rfidResult.status==='OK'?'✅ CORRECT':'❌ WRONG SHELF'}</Text>
                    <Text style={s.btit}>{rfidResult.title}</Text>
                    <Text style={s.bsub}>
                      UID: {rfidResult.uid}{'\n'}
                      Book #: {rfidResult.bookNumber||'—'}{'\n'}
                      Author: {rfidResult.author||'—'}{'\n'}
                      Programme: {rfidResult.programme||'—'}{'\n'}
                      Rack: {rfidResult.rack}{'\n'}
                      Expected: {rfidResult.expectedShelf} | Scanned: {rfidResult.currentShelf}
                    </Text>
                  </>
                )}
              </View>
            )}
          </View>
        )}

        {tab==='shelves' && (
          <View>
            <Text style={s.h1}>Shelf Map</Text>
            {SHELVES.map(sh => (
              <View key={sh.id} style={s.shcard}>
                <Text style={s.shid}>{sh.id}</Text>
                <Text style={s.shcat}>{sh.cat} — {sh.n} books</Text>
                <View style={s.barBg}>
                  <View style={[s.barFill,{width:Math.round(sh.n/sh.cap*100)+'%'}]}/>
                </View>
              </View>
            ))}
          </View>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safe:{flex:1,backgroundColor:'#0f1117'},
  tabs:{flexDirection:'row',backgroundColor:'#1a1d27',borderBottomWidth:1,borderColor:'#2e3249'},
  tab:{flex:1,paddingVertical:13,alignItems:'center'},
  tabActive:{borderBottomWidth:2,borderColor:'#6c5ce7'},
  tabTxt:{color:'#8b90a7',fontSize:12,fontWeight:'600'},
  tabTxtActive:{color:'#6c5ce7'},
  body:{flex:1,padding:16},
  h1:{color:'#e8eaf0',fontSize:20,fontWeight:'800',marginBottom:4,marginTop:8},
  sub:{color:'#8b90a7',fontSize:12,marginBottom:16},
  lbl:{color:'#8b90a7',fontSize:11,fontWeight:'700',marginTop:12,marginBottom:4,
    textTransform:'uppercase',letterSpacing:0.5},
  inp:{backgroundColor:'#22263a',borderWidth:1,borderColor:'#2e3249',
    borderRadius:8,padding:11,color:'#e8eaf0',fontSize:14,marginBottom:4},
  row:{flexDirection:'row',marginBottom:10},
  btn:{padding:13,borderRadius:8,alignItems:'center',justifyContent:'center'},
  btnBlue:{backgroundColor:'#6c5ce7'},
  btnGreen:{backgroundColor:'#00b894'},
  btnT:{color:'#fff',fontWeight:'700',fontSize:14},
  img:{width:'100%',height:220,borderRadius:8,marginVertical:8,backgroundColor:'#000'},
  card:{backgroundColor:'#1a1d27',borderRadius:10,padding:14,marginTop:12,
    borderWidth:1,borderColor:'#2e3249'},
  cardH:{color:'#a29bfe',fontWeight:'700',fontSize:14,marginBottom:10},
  brow:{backgroundColor:'#22263a',borderRadius:8,padding:10,marginTop:6,borderLeftWidth:4,borderColor:'#2e3249'},
  bok:{borderColor:'#00b894'},
  bwr:{borderColor:'#e17055'},
  btit:{color:'#e8eaf0',fontSize:13,fontWeight:'700'},
  bsub:{color:'#8b90a7',fontSize:12,marginTop:3,lineHeight:18},
  shcard:{backgroundColor:'#1a1d27',borderRadius:10,padding:14,marginBottom:10,
    borderWidth:1,borderColor:'#2e3249'},
  shid:{color:'#6c5ce7',fontSize:22,fontWeight:'800'},
  shcat:{color:'#8b90a7',fontSize:12,marginBottom:8},
  barBg:{height:5,backgroundColor:'#2e3249',borderRadius:3,overflow:'hidden'},
  barFill:{height:5,backgroundColor:'#00b894',borderRadius:3},
});
