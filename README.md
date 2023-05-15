# DDDTools
自分用に作った雑多なツールをアドオンとしてまとめたものです。  
Blender 3.1 以降用。  
エラー処理が甘かったりするので、自己責任でお使いくださいませ。  

## インストール
[Release](https://github.com/DaDaDan3D/DDDTools/releases) から最新版をダウンロードし、Blender の 編集 > プリファレンス > アドオン からインストールしてください。  

## 使い方
ビューの右上の < を押すかキーボードの N を押すかすると出てくるツールシェルフの DDDTools タブにパネルがまとまっています。  

## EditTool
![EditTool](/images/Panel_EditTool.png)

### EditTool / 分割線の選択
四角形を単純に二つに分割するエッジループを、様々な条件で選択したり、そのまま溶解してポリゴン数を削減したりするツールです。  
サブディビジョンサーフェスモディファイアやループカットツールなどで増えすぎたポリゴンを減らすのに使えます。  
四角形を四角形のままでポリゴン数を減らすので、形状が崩れにくく、また、再びサブディビジョンサーフェスなどをかけたりすることも容易にできます。  

![SelectDividingLoop](/movies/BlenderSelectDividingLoopCompare.mp4)

### EditTool / 近似球の追加
選択した頂点に近似した球オブジェクトを追加します。  
頂点は 4 つ以上選択している必要があります。  
(点郡の球面近似アルゴリズムはDr.レオさん作の fitting.py を使用させていただいております)  
https://programming-surgeon.com/script/sphere-fit/  

### EditTool / エンプティ球の追加
「近似球の追加」のエンプティ版です。メッシュのかわりにエンプティ球を追加します。

### EditTool / エンプティとメッシュの相互変換
選択したオブジェクトを変換します。
オブジェクトがメッシュの場合は近似したエンプティ球に、エンプティの場合はメッシュ球に変換します。
コライダの調整をする時に便利です。

![ConvertEmptyAndSphere](/images/ConvertEmptyAndSphere.png)

## MaterialTool
![MaterialTool](/images/Panel_MaterialTool.png)

### MaterialTool / テクスチャ関係 / オブジェクト選択
指定したテクスチャを使っているオブジェクトを選択します。  

### MaterialTool / テクスチャ関係 / マテリアル列挙
指定したテクスチャを使っているマテリアルを情報に表示します。  

### MaterialTool / テクスチャ関係 / 全マテリアルを設定
アクティブなオブジェクトに対して、既存のマテリアルの割り当てを解除した後、指定したテクスチャを使っているマテリアルを全て登録します。  
マテリアル一覧的な使い方ができます。  

### MaterialTool / テクスチャ関係 / シェーダーノード選択
指定したテクスチャを使っているマテリアルのシェーダーノードを選択してアクティブ状態にします。  
テクスチャをベイクする時などに使います。  

### MaterialTool / マテリアル関係 / オブジェクト選択
指定したマテリアルを使っているオブジェクトを選択します。  

### MaterialTool / マテリアル関係 / オブジェクト列挙
指定したテクスチャを使っているオブジェクトを情報に表示します。  

### MaterialTool / マテリアルのソート
選択したオブジェクトのマテリアルスロットを、マテリアル順指定リストを参照してソートします。  
具体的には、マテリアルスロットのマテリアルを、マテリアル順指定リストにある順番→名前の順番、という風に並べます。  

## VRMTool
![VRMTool](/images/Panel_VRMTool.png)

### VRMTool / コライダー関係 / 不要エンプティ削除
指定したアーマチュアの、UI に表示されない隠れたエンプティを削除します。  
通常は使うことはありません。  

### VRMTool / コライダー関係 / エンプティのコライダ化
選択したエンプティを、アクティブなアーマチュアのアクティブなボーンのコライダとして設定します。  
「リネームする」をオンにした場合、「Collider_Arm_L」というような名前に自動的にリネームします。  
「ミラーの作成」をオンにした場合、次の「コライダのミラーを作成」を自動的に実行します。  

### VRMTool / コライダー関係 / コライダのミラーを作成
選択したコライダの複製を作成し、ミラーとして名前や位置や大きさを設定します。  
親が「Arm_L」などの、左右のあるボーンの場合には「Arm_R」のコライダが作られます。  
親が「Hips」などの、左右のないボーンの場合には、対称な位置にコライダが作られます。  

### VRMTool / コライダ追加
ポーズモード時、アクティブなボーンに対して、指定したメッシュに沿うようなサイズの Empty 球を追加します。  
具体的には、ボーンに沿った方向で一定間隔に、ボーンを軸として放射状にレイを飛ばし、メッシュとの交点を近似するような球をコライダとして作成します。  
実行後、プロパティパネルで調整ができます。    

![Panel_AddCollider](/images/Panel_AddCollider.png)

「終了位置を自動計算」をオンにした場合、ボーンの tail を超えないような位置までコライダを作成します。オフにした場合、「終了位置」で指定された位置までコライダを作成します。  
「レイの最大半径」は、レイとメッシュとの交点の計算に使用します。コライダの最大半径と考えて良いです。
「レイの方向」が「内から広がる」の場合、ボーンから外側に向かってレイを飛ばします。
「外から集まる」の場合、外側からボーンに向かってレイを飛ばします。
メッシュが凸なのか凹なのかによって使いわけてください。
大抵の場合は「内から広がる」で良いと思います。  

![AddCollider](/images/AddCollider.png)

### VRMTool / VRM 出力前の準備
モデルを VRM としてエクスポートするための準備をします。  
ポーズアセットを使って表情を付ける仕組みとして設計されています。  
ポーズアセットを使うことでシェイプキーを使わなくて済むので、エクスポート後にモデルを修正するといった手戻りに強くなります。  
[blendshape_group.json のサンプル](/sample/blendshape_group.json)
[spring_bone.json のサンプル](/sample/spring_bone.json)

「VRM 出力前の準備」ボタンを押すと、具体的には、指定したアーマチュアに対して以下の操作を行います。(オプションでオンオフできる箇所もあります)  

1. VRM Addon for Blender の BlendShape の情報を削除する
1. spring_bone.json を指定した場合、VRM Addon for Blender の SpringBone の情報を削除する
1. 透明なポリゴンを削除する。具体的にやっていることは後述の「ポリゴン削除」を参照
1. blendshape_group.json の内容に応じて、メッシュを一つにまとめる。
具体的には、binds の mesh で指定した名前の Collection を探し、Collection に含まれるメッシュのモディファイアを適用した後、一つにする
1. blendshape_group.json の内容に応じて、ポーズアセットをシェイプキーとしてメッシュにベイクする。
具体的には、binds の index で指定した名前のポーズアセットを、前段階で一つにまとめたメッシュに対して、シェイプキーとして保存する
1. 「出力しない骨」として指定したボーングループの骨を溶解する
1. ウェイトのクリーンアップを行う
1. 未使用マテリアルを削除する
1. MaterialTool パネルの「マテリアル順指定リスト」を参照し、マテリアルのソートを行う
1. blendshape_group.json の内容をアーマチュアに登録する
1. spring_bone.json の内容に従い、コライダを登録し、不要なエンプティがあれば削除する
1. *.export.blend として名前を付けて保存する

### VRMTool / ポリゴン削除
メッシュのテクスチャをスキャンし、透明なポリゴンを削除するための設定です。  
チェックを付けると「VRM 出力前の準備」で自動的に呼ばれますし、「削除実行」ボタンを押すことで即座に削除することもできます。  
具体的には、不透明なテクセルが一つも含まれないポリゴンを透明なポリゴンと見なして削除します。
ただし、下記の「除外マテリアルリスト」で指定したマテリアル及び、MToon_unversioned でオートスクロールが設定されているマテリアルのポリゴンは削除されません。  
「判定の粗さ」は、テクスチャをスキャンする時にどれだけドットを間引くかの指定です。4 なら 1/4 (面積なら 1/16)になるので、大きな値を指定すればするほど高速になります。  
「アルファ値の閾値」は、アルファブレンドとアルファハッシュのマテリアルで透明と見なすアルファ値の指定です。
アルファクリップではマテリアルに設定されている値を閾値として使用します。  
「除外マテリアルリスト」は、削除対象から除外するマテリアルの指定です。
透明だが削除されたくないマテリアルなどを指定します。  

![RemoveTransparentPolygons](/movies/BlenderRemoveTransparentPolygons.mp4)


## BoneTool
![BoneTool](/images/Panel_BoneTool.png)

### BoneTool / 子ボーンをリネーム
アクティブなボーンの子供のボーンの名前を、番号付きでリネームします。  

### BoneTool / リセットストレッチ
アクティブなアーマチュアに含まれる全てのボーンのストレッチモディファイアの長さをリセットします。  

### BoneTool / 現在の姿勢をレストポーズに
アクティブなアーマチュアの現在の姿勢をレストポーズとして設定します。  
アーマチュアによって変形するメッシュの状態もそのまま保とうとするので、A ポーズを T ポーズにしたい時などに使えます。  
非表示のオブジェクトは修正しないので、注意して使い分けてください。

## WeightTool
![WeightTool](/images/Panel_WeightTool.png)

### WeightTool / ウェイトのリセット
選択した全てのメッシュのウェイトをゼロにリセットします。  

### WeightTool / ウェイトのクリーンアップ
選択した全てのメッシュに対して以下の操作を行います。
1. 対応するボーンの存在しない頂点グループを削除
1. 「クリーン」 0.001 未満のウェイトの割り当てを削除 
1. 「合計を制限」 影響を与えるボーンの数が 4 以下になるように制限
1. 「すべてを正規化」 ウェイトの合計が 1 になるように正規化
1. 頂点グループに対して「ボーン階層でソート」

### WeightTool / ウェイトの転送
選択した全てのメッシュに対して、指定したメッシュから頂点ウェイトを転送します。  
ワンボタンで転送できるので、データ転送モディファイアやウェイトペイントを使うよりも楽です。  

### WeightTool / 頂点の左右ウェイト均一化
選択した全ての頂点に対して、左右のボーンに均等にウェイトが乗るようにします。  
ただし、ボーンの名前の末尾が \_L, \_R, -L, -R, .L, .R になっている必要があります。(番号ではダメ)  
例えば Arm_L:0.2 Arm_R:0.5 になっているような頂点は Arm_L:0.35 Arm_R:0.35 になります。  
ミラーの境界面上の点に対して実行すると良いです。  

### WeightTool / 選択した骨の溶解
選択した全てのボーンに対して、頂点ウェイトを直近の祖先の変形ボーンに移し替えて溶解します。  
スキニングが終わった後に中間のボーンを溶解したくなった時に便利です。  

## NormalTool
![NormalTool](/images/Panel_NormalTool.png)

### NormalTool / カスタム法線
選択したメッシュのカスタム法線をオンオフします。  

## UVTool
![UVTool](/images/Panel_UVTool.png)

### UVTool / 整列
UV エディタの 2D カーソル位置を基準に、選択した UV を上下左右にぴったりくっつけます。  
中心の数値は 2D カーソルの座標です。  
ミラーモディファイアで「ミラーU」や「ミラーV」を使う時に便利です。  

### UVTool / 移動
UV エディタで、選択した UV を上下左右に移動させます。  
中心の数値は、移動量です。  

## ShaderTool
![ShaderTool](/images/Panel_ShaderTool.png)

### ShaderTool / スペキュラ計算
指定した IOR (屈折率 Index of Refraction) を元に、スペキュラを計算してクリップボードにコピーします。  
スペキュラは以下の式で計算されます。  
$specular=((ior−1)/(ior+1))^2$
https://docs.blender.org/manual/ja/2.90/render/shader_nodes/shader/specular_bsdf.html

### ShaderTool / グループノード置換
指定したグループノードを、別のグループノードに置き換え、設定をコピーします。  
VRM Addon for Blender の過去のバージョンの MToon_unversioned を、新しいバージョンのものに置き換えるのに便利です。  

### ShaderTool / ノードインプット一覧
選択したオブジェクトで使用されているマテリアルのノードの、特定のインプットを一覧表示して編集できます。  
オブジェクトを選択した後、最初に「ノード名」を選びます。
次に、「インプット」を選び、「リスト作成」ボタンを押すと、下に一覧が作成されます。  
一覧で直接編集することもできますし、左の目のマークを押せば、エディタにマテリアルを表示することもできます。  
右の×ボタンを押せば、一覧から取り除くことができます。
(一覧から取り除かれているだけなので元のマテリアルには影響はありません)  
一覧で項目を選び、下の「値をコピー」ボタンを押すと、選択した項目の内容を一覧すべてにコピーします。  

![ShaderToolSample](/images/Blender_EditMaterialInputNodes.png)

## 免責
このアドオンを使用して生じたいかなる損害に対しても、当方は責任を負いません。  
自己責任でご使用ください。  


## License
MIT



